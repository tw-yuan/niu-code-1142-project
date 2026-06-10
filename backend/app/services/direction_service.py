import json
import re
from openai import AsyncOpenAI
from app.config import settings

FIXED_DIRECTIONS = [
    {
        "key": "qa",
        "label": "深入問答",
        "description": "針對任何問題自由提問，獲得基於講義的深入解答",
        "emoji": "💬",
        "is_dynamic": False,
    },
    {
        "key": "summary",
        "label": "章節摘要",
        "description": "生成各章節重點摘要，快速掌握課程架構",
        "emoji": "📝",
        "is_dynamic": False,
    },
    {
        "key": "explain",
        "label": "觀念解釋",
        "description": "深入解釋課程中的重要概念，以例子說明",
        "emoji": "🧠",
        "is_dynamic": False,
    },
    {
        "key": "quiz",
        "label": "自我測驗",
        "description": "生成測驗題目，即時批改並解析答案",
        "emoji": "📋",
        "is_dynamic": False,
    },
]

DIRECTION_SYSTEM_PROMPTS = {
    "qa": "你是一位學業助理。請嚴格根據提供的講義內容回答學生的問題。若問題超出講義範圍，請說明並盡量提供相關說明。請以繁體中文回答。",
    "summary": "你是一位學業助理。請根據提供的講義內容，系統化整理各章節或段落的重點摘要，以條列方式呈現，幫助學生快速複習。請以繁體中文回答。",
    "explain": "你是一位學業助理。請根據提供的講義內容，深入解釋學生詢問的概念，並舉例說明，連結相關的知識脈絡。請以繁體中文回答。",
    "quiz": (
        "你是一位學業助理，扮演出題老師的角色。根據提供的講義內容出測驗題目，"
        "等待學生回答後給予評分與詳細解析。請一次出 3-5 題，並在學生回答後逐題批改。"
        "請以繁體中文出題並批改。"
    ),
}

DEFAULT_DYNAMIC_PROMPT = "你是一位學業助理，請根據提供的講義內容協助學生學習。請以繁體中文回答。"

INTEGRITY_POLICY = (
    "你必須遵守學術誠信：不要替學生直接完成可繳交作業、考試答案或規避偵測；"
    "遇到這類要求時，改以提示、解題步驟、檢核清單、概念說明或練習題協助學習。"
)


def get_direction_system_prompt(direction_key: str, dynamic_hint: str | None = None) -> str:
    if direction_key in DIRECTION_SYSTEM_PROMPTS:
        return f"{DIRECTION_SYSTEM_PROMPTS[direction_key]}\n\n{INTEGRITY_POLICY}"
    if dynamic_hint:
        return f"你是一位學業助理，專注於「{dynamic_hint}」這個學習方向。請根據提供的講義內容協助學生。請以繁體中文回答。\n\n{INTEGRITY_POLICY}"
    return f"{DEFAULT_DYNAMIC_PROMPT}\n\n{INTEGRITY_POLICY}"


async def generate_dynamic_directions(doc_text: str) -> list[dict]:
    preview = doc_text[:3000]

    oai = AsyncOpenAI(
        base_url=settings.openai_compatible_base_url,
        api_key=settings.openai_compatible_api_key or "none",
    )

    prompt = (
        "以下是一份課程講義的部分內容。請分析這份講義的主題和內容，"
        "生成 4 個最適合這份講義的客製化學習方向。\n\n"
        "要求：\n"
        "1. 每個方向必須是具體且與講義內容直接相關的\n"
        "2. 方向應該對學生有實際學習價值\n"
        "3. 請以 JSON 陣列格式回傳，每個物件包含：key（英文識別符）、label（繁體中文簡短名稱）、"
        "description（繁體中文一句話說明）、emoji（1個適合的 emoji）\n\n"
        "講義內容：\n"
        f"{preview}\n\n"
        "請直接回傳 JSON 陣列，不要加其他說明文字。範例格式：\n"
        '[{"key": "formula_practice", "label": "公式練習", "description": "針對講義中的公式逐一練習與推導", "emoji": "🔢"}]'
    )

    try:
        response = await oai.chat.completions.create(
            model=settings.openai_compatible_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )
        raw = response.choices[0].message.content.strip()
        # 模型可能輸出 <think> 區塊或 ```json 圍欄，直接抓最外層的 JSON 陣列
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return []
        dynamic = json.loads(raw[start : end + 1])
        for d in dynamic:
            d["is_dynamic"] = True
        return dynamic[:4]
    except Exception:
        return []


async def get_directions(doc_text: str) -> list[dict]:
    dynamic = await generate_dynamic_directions(doc_text)
    return FIXED_DIRECTIONS + dynamic
