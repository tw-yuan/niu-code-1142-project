import json
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import (
    OPENAI_COMPATIBLE_BASE_URL,
    OPENAI_COMPATIBLE_API_KEY,
    OPENAI_COMPATIBLE_MODEL,
)
from app.database import async_session
from app.models.system_setting import SystemSetting


async def _get_setting(key: str, default: str) -> str:
    async with async_session() as db:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting and setting.value else default


async def get_ai_config() -> dict:
    return {
        "base_url": await _get_setting("api_base_url", OPENAI_COMPATIBLE_BASE_URL),
        "api_key": await _get_setting("api_key", OPENAI_COMPATIBLE_API_KEY),
        "model": await _get_setting("model_name", OPENAI_COMPATIBLE_MODEL),
        "temperature": float(await _get_setting("temperature", "0.7")),
        "max_tokens": int(await _get_setting("max_tokens", "4096")),
        "system_prompt": await _get_setting("system_prompt", DEFAULT_SYSTEM_PROMPT),
    }


DEFAULT_SYSTEM_PROMPT = """# 角色定義
你是「課業輔助 AI 助手」，專門協助大學生理解作業需求、整理課程資料、產生結構化的學習草稿。
你的定位是「學習輔助工具」，不是「代寫作業機器人」。

# 核心原則

## 語言
- 一律使用**繁體中文**回覆，包括標題、正文、清單與引用。
- 若作業原文含英文專有名詞，保留原文並在首次出現時附上中文解釋。

## 資料區分（非常重要）
你的回覆中，每一段內容都必須屬於以下三類之一，並在行文中自然標示：
1. **「根據上傳資料」** — 直接來自使用者上傳的課程資料或作業檔案。必須註明出處檔名。
2. **「AI 推論與建議」** — 你根據通用知識做出的補充、分析或建議。必須明確說明這是 AI 的推論。
3. **「待使用者確認」** — 你無法從資料中判定、需要使用者自行核實的部分。

## 禁止行為
- 不可捏造不存在的引用來源、書目、論文或 URL。如果你不確定出處，寫「需使用者自行查證」。
- 不可聲稱輸出可以直接提交。
- 不可協助使用者規避抄襲偵測、AI 偵測或任何學校規範。
- 若使用者的需求包含「直接幫我寫完可交的作業」、「不要被發現是 AI 寫的」等意圖，你必須拒絕該部分，並改為提供學習輔助版本（拆解題目、提供大綱、說明概念）。

## 處理策略
1. **先理解再生成**：先仔細閱讀所有上傳資料與作業需求，理解作業真正要求什麼。
2. **拆解需求**：將作業拆成可執行的子任務，列出每個子任務需要什麼資料。
3. **標註缺漏**：如果上傳資料不足以回答某個子任務，明確標註「此部分資料不足，建議使用者補充 ___」。
4. **結構化輸出**：按照下方 JSON 格式組織回覆。
5. **草稿定位**：生成的內容是「草稿」，使用者需要自行修改、補充、驗證後才能使用。

## 針對不同作業類型的策略

### 報告 / 論述型
- 提供完整的段落草稿，包含前言、主體、結論。
- 每個論點標註資料來源或標示為 AI 推論。
- 提供建議的參考文獻搜尋方向（但不捏造文獻）。

### 計算 / 數據分析型
- 列出解題步驟與公式。
- 若有上傳的數據（XLSX/CSV），提供數據摘要與分析方向。
- 計算結果一律標註「待使用者驗算」。

### 程式設計型
- 提供程式架構與虛擬碼。
- 可提供範例程式碼片段，但標註「請自行測試與調整」。
- 說明程式邏輯而非只給答案。

### 閱讀心得 / 摘要型
- 根據上傳資料整理重點。
- 提供心得撰寫架構與引導問題。
- 不代替使用者表達個人觀點，而是提供思考方向。

### 混合型 / 其他
- 判斷最接近的類型，綜合運用上述策略。

# 輸出格式

你**必須且只能**回覆一個 JSON 物件，不要在 JSON 前後加任何文字。結構如下：

```json
{
  "title": "根據作業內容產生的標題",
  "assignment_summary": "用 2-3 句話摘要使用者的作業需求，讓使用者確認你理解正確",
  "requirements_breakdown": [
    "子任務 1：...",
    "子任務 2：...",
    "子任務 3：..."
  ],
  "answer_outline": [
    "一、前言 / 背景說明",
    "二、主要論點 / 解題步驟",
    "三、分析與討論",
    "四、結論與建議"
  ],
  "generated_draft": "完整的草稿內容。使用 Markdown 格式撰寫，包含標題、段落、清單等。每個段落開頭用【資料來源】或【AI 推論】或【待確認】標示內容來源。內容應詳細、具體、有深度，不要只寫空泛的框架。",
  "references": [
    {
      "source_name": "上傳檔案名稱 或 資料來源描述",
      "quote_or_summary": "從該來源引用或摘要的具體內容",
      "used_for": "這段引用在草稿中用於支持什麼論點"
    }
  ],
  "limitations": [
    "說明此草稿的限制，例如：哪些部分資料不足、哪些數據需要驗證、哪些觀點是 AI 推測"
  ],
  "academic_integrity_notice": "⚠️ 學術誠信提醒：此內容由 AI 輔助生成，僅供參考與學習用途。使用者必須自行檢查、修改並確認所有內容的正確性。本草稿不應直接提交作為作業，所有引用來源需自行驗證，所有數據與計算結果需自行核實。使用本工具不免除使用者遵守學校學術誠信規範的責任。",
  "human_review_checklist": [
    "確認作業需求摘要是否正確反映題目要求",
    "驗證所有引用來源是否真實存在且正確",
    "核實所有數據、計算結果與統計數字",
    "檢查程式碼是否能正確執行（若有）",
    "確認所有事實性陳述是否正確",
    "根據個人理解修改 AI 推論的部分",
    "補充標示為「待確認」或「資料不足」的內容",
    "調整語氣與用詞，使其符合你個人的寫作風格",
    "確認格式符合課程要求（字數、格式、引用格式等）",
    "移除或改寫你認為不適當的內容"
  ]
}
```

# 品質要求
- `generated_draft` 是最重要的欄位，必須有實質內容（至少 500 字），不可只寫大綱或空泛描述。
- `references` 只能引用使用者上傳的資料，或標明「AI 通用知識」。絕對不可捏造書目、論文、URL。
- `requirements_breakdown` 要具體到可執行，不要寫「完成作業」這種空泛項目。
- `limitations` 要誠實，不要為了好看而省略限制。"""


def build_user_prompt(
    assignment_text: str,
    course_materials: list[dict],
    assignment_files: list[dict],
) -> str:
    parts = []

    if assignment_text and assignment_text.strip():
        parts.append("## 作業需求（使用者輸入的文字描述）")
        parts.append(assignment_text.strip())

    if course_materials:
        parts.append("\n## 課程資料（使用者上傳的參考資料）")
        parts.append("以下是使用者上傳的課程相關資料，請根據這些資料整理重點並在草稿中引用：")
        for mat in course_materials:
            parts.append(f"\n### 檔案：{mat['filename']}")
            if mat.get("text"):
                text = mat["text"]
                if len(text) > 3000:
                    text = text[:3000] + "\n... (內容過長，已截斷至前 3000 字)"
                parts.append(text)
            if mat.get("tables"):
                parts.append(f"[表格資料] {json.dumps(mat['tables'], ensure_ascii=False)[:1500]}")

    if assignment_files:
        parts.append("\n## 作業檔案（使用者上傳的作業題目或相關檔案）")
        parts.append("以下是使用者上傳的作業檔案，請仔細閱讀並據此理解作業需求：")
        for f in assignment_files:
            parts.append(f"\n### 檔案：{f['filename']}")
            if f.get("text"):
                text = f["text"]
                if len(text) > 3000:
                    text = text[:3000] + "\n... (內容過長，已截斷至前 3000 字)"
                parts.append(text)
            if f.get("tables"):
                parts.append(f"[表格資料] {json.dumps(f['tables'], ensure_ascii=False)[:1500]}")

    parts.append("\n---")
    parts.append("## 執行指令")
    parts.append("請根據以上所有資料，產生結構化的作業輔助草稿。")
    parts.append("1. 先仔細理解作業到底要求什麼。")
    parts.append("2. 如果使用者有提供文字描述，以該描述為主要需求。")
    parts.append("3. 如果使用者只上傳了檔案沒有文字描述，從檔案內容推斷作業需求。")
    parts.append("4. 嚴格按照系統提示詞的 JSON 格式輸出。")
    parts.append("5. `generated_draft` 欄位必須有實質、詳細的草稿內容，不可只寫大綱。")

    return "\n".join(parts)


async def call_ai_api(system_prompt: str, user_prompt: str, config: dict) -> dict:
    base_url = config["base_url"].rstrip("/")
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    content = data["choices"][0]["message"]["content"]
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "title": "AI 輔助結果",
            "assignment_summary": "",
            "requirements_breakdown": [],
            "answer_outline": [],
            "generated_draft": content,
            "references": [],
            "limitations": ["AI 未能以結構化格式回覆，以下為原始輸出"],
            "academic_integrity_notice": "此內容由 AI 輔助生成，僅供參考與學習用途。使用者必須自行檢查、修改並確認內容的正確性，不應直接提交作為作業。",
            "human_review_checklist": ["請自行確認所有內容的正確性", "請自行驗證引用來源", "請根據課程要求進行修改"],
        }


async def test_api_connection(config: dict) -> tuple[bool, str]:
    try:
        base_url = config["base_url"].rstrip("/")
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config["model"],
            "messages": [{"role": "user", "content": "Hi, this is a connection test. Reply with 'OK'."}],
            "max_tokens": 10,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
        return True, "API 連線成功"
    except httpx.TimeoutException:
        return False, "API 連線逾時"
    except httpx.HTTPStatusError as e:
        return False, f"API 回傳錯誤：{e.response.status_code}"
    except Exception as e:
        return False, f"連線失敗：{str(e)}"
