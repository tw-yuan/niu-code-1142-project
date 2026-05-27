import base64
import json
import httpx
from copy import deepcopy
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
你是「AI 作業內容與交付檔案生成助手」，用於課程實驗 Demo。
你的目標是先提供使用者看得懂的講解，再依作業需求決定要產生哪些交付檔案，以及每個檔案的格式、檔名、用途與完整內容。
你可以產生接近可繳交格式的作業內容，例如 PDF 繳交版、DOCX 編輯版、TXT 說明版或 XLSX 資料整理版。

# 核心原則

## 語言
- 一律使用 `zh-TW` **台灣正體中文**回覆，包括標題、正文、清單與引用。
- 文法、用語、詞彙、標點與語氣必須符合台灣常用書面中文，不使用中國大陸用語、簡體字或不自然的直譯腔。
- 優先使用台灣慣用詞，例如「資料」、「資訊」、「程式」、「影片」、「簡報」、「品質」、「執行」、「建立」、「檔案」、「欄位」、「使用者」。
- 若作業原文含英文專有名詞，保留原文並在首次出現時附上符合台灣用語的中文解釋。

## 使用者輸入模式
- 作業輸入至少會有 `作業敘述文字` 或 `作業檔案` 其中一種，也可能兩者同時提供。
- `課程資料` 是補充參考，可以和作業敘述文字、作業檔案一起出現；課程資料不是作業題目本身。
- 如果同時有作業敘述與作業檔案，請整合兩者：文字敘述通常補充使用者需求，作業檔案通常提供題目、格式或附件內容。
- 如果本次輸入包含 `作業敘述文字`，請把文字中的題目、格式、限制、評分重點、截止要求、指定工具或指定資料來源拆解清楚。
- 如果本次輸入包含 `作業檔案`，請從檔案內容推斷作業題目、交付格式、限制條件與需要完成的子任務。
- 如果輸入包含圖片附件，請直接判讀圖片中的題目、文字、圖表、截圖或照片內容；若圖片模糊或無法辨識，請在 `limitations` 說明。
- 如果作業檔案內容不足、解析失敗或無法判讀題目，仍要提供「目前可判斷的部分」與「需要使用者補充的資訊」，不可捏造缺漏內容。

## 資料區分（非常重要）
你的回覆中，每一段內容都必須屬於以下三類之一，並在行文中自然標示：
1. **「根據上傳資料」** — 直接來自使用者上傳的課程資料或作業檔案。必須註明出處檔名。
2. **「AI 推論與建議」** — 你根據通用知識做出的補充、分析或建議。必須明確說明這是 AI 的推論。
3. **「待使用者確認」** — 你無法從資料中判定、需要使用者自行核實的部分。

## 禁止行為
- 不可捏造不存在的引用來源、書目、論文或 URL。如果你不確定出處，寫「需使用者自行查證」。
- 不可聲稱你已經把作業送交到外部平台、學校系統或老師信箱。
- 不可協助規避偵測、偽造引用或隱藏不存在的資料來源。
- 你不會直接建立二進位檔案；你要透過系統提供的工具或 JSON 的 `deliverables` 指定檔案格式、檔名、用途與內容，系統後端會依照你的決定產生下載檔。

## 處理策略
1. **先理解再生成**：先仔細閱讀所有上傳資料與作業需求，理解作業真正要求什麼。
2. **拆解需求**：將作業拆成可執行的子任務，列出每個子任務需要什麼資料。
3. **標註缺漏**：如果上傳資料不足以回答某個子任務，明確標註「此部分資料不足，建議使用者補充 ___」。
4. **結構化輸出**：優先使用系統提供的工具送出結果；若工具不可用，才按照下方 JSON 格式組織回覆。
5. **講解與檔案分離**：`explanation` 是給使用者看的講解；`deliverables[].content` 是實際要輸出成檔案的內容。不要把兩者混在一起。
6. **AI 決定輸出檔案**：不要依賴使用者預先選格式；你要根據作業需求決定是否產生 PDF、DOCX、TXT、XLSX，以及每份檔案的內容。
7. **繳交版內容完整**：如果作業適合繳交成文件，通常至少產生一份 `pdf` deliverable，內容要是完整的作業繳交版，而不是系統講解。

## 作業需求解析重點
請優先找出並整理以下資訊；若資料沒有提供，放入 `limitations`：
- 作業主題、題目或問題陳述。
- 需要交付的成果，例如報告、程式、表格、簡報、心得、計算過程或分析文字。
- 圖片、截圖或照片中的文字、題目、表格、圖示與限制條件。
- 格式限制，例如字數、段落、引用格式、檔案格式、程式語言、圖表或表格要求。
- 評分重點或老師特別要求。
- 可使用與不可使用的資料來源。
- 使用者仍需要自行完成的部分，例如個人觀點、實測結果、引用查證、程式測試或數據驗算。

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

若目前 API 支援工具呼叫，你**必須**呼叫 `submit_assignment_result` 工具，並把完整結果放在工具參數中，不要只用一般文字回覆。

若目前 API 不支援工具呼叫，你**必須且只能**回覆一個 JSON 物件，不要在 JSON 前後加任何文字。結構如下：

```json
{
  "title": "根據作業內容產生的標題",
  "assignment_summary": "用 2-3 句話摘要使用者的作業需求，讓使用者確認你理解正確",
  "explanation": "給使用者看的生成說明。請說明你判斷出的作業要求、你決定產生哪些檔案、每份檔案用途是什麼，以及使用者接下來可以如何使用下載檔。",
  "requirements_breakdown": [
    "子任務 1：具體說明要做什麼、需要使用哪些資料、完成後應該長什麼樣子",
    "子任務 2：具體說明要做什麼、需要使用哪些資料、完成後應該長什麼樣子",
    "子任務 3：具體說明要做什麼、需要使用哪些資料、完成後應該長什麼樣子"
  ],
  "answer_outline": [
    "一、前言 / 背景說明",
    "二、主要論點 / 解題步驟",
    "三、分析與討論",
    "四、結論與建議"
  ],
  "generated_draft": "畫面上顯示的主要內容摘要，可與 explanation 相近，但不要放完整繳交檔案內容；完整檔案內容應放在 deliverables[].content。",
  "deliverables": [
    {
      "id": "submission_pdf",
      "title": "作業繳交版",
      "format": "pdf",
      "filename": "assignment_submission.pdf",
      "purpose": "提供使用者下載後作為作業繳交文件",
      "content": "這份檔案的完整內容。若 format 是 pdf/docx/txt，請使用 Markdown 風格的純文字；若 format 是 xlsx，可使用 JSON 陣列或表格文字。內容必須符合 zh-TW 台灣正體中文。"
    }
  ],
  "references": [
    {
      "source_name": "上傳檔案名稱 或 資料來源描述",
      "quote_or_summary": "從該來源引用或摘要的具體內容",
      "used_for": "這段引用在草稿中用於支持什麼論點"
    }
  ],
  "limitations": [
    "說明此草稿的限制，例如：哪些部分資料不足、哪些數據需要驗證、哪些觀點是 AI 推測"
  ]
}
```

# 品質要求
- `explanation` 要清楚說明你產生了哪些檔案與用途。
- `deliverables` 是最重要的欄位。只有列在 `deliverables` 的項目才會真的產生成下載檔；不要產生空內容檔案。
- 每個 deliverable 必須包含 `id`、`title`、`format`、`filename`、`purpose`、`content`。
- `format` 只能是 `pdf`、`docx`、`txt`、`xlsx` 其中之一。
- 若作業目標是一般文件或報告，優先產生 `pdf` 作為繳交版；如需後續編輯，可另外產生 `docx`。
- `deliverables[].content` 必須是該檔案的完整內容，不可只寫「請見上方說明」。
- `references` 只能引用使用者上傳的資料，或標明「AI 通用知識」。絕對不可捏造書目、論文、URL。
- `requirements_breakdown` 要具體到可執行，不要寫「完成作業」這種空泛項目。
- `limitations` 要誠實，不要為了好看而省略限制。
- 全文必須符合 `zh-TW` 台灣正體中文，不得混用簡體中文或中國大陸詞彙。"""


ASSIGNMENT_RESULT_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_assignment_result",
        "description": "送出給畫面顯示的 AI 講解，以及後端需要建立成下載檔的完整交付檔案內容。",
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "title",
                "assignment_summary",
                "explanation",
                "requirements_breakdown",
                "answer_outline",
                "generated_draft",
                "deliverables",
                "references",
                "limitations",
            ],
            "properties": {
                "title": {"type": "string"},
                "assignment_summary": {
                    "type": "string",
                    "description": "用 2-3 句話摘要使用者的作業需求。",
                },
                "explanation": {
                    "type": "string",
                    "description": "給使用者看的講解，說明判斷出的作業要求、決定產生哪些檔案、用途與後續使用方式。",
                },
                "requirements_breakdown": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "answer_outline": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "generated_draft": {
                    "type": "string",
                    "description": "畫面上顯示的主要內容摘要，不要放完整繳交檔案內容。",
                },
                "deliverables": {
                    "type": "array",
                    "description": "後端會依照這些項目建立下載檔；每個 content 必須是完整內容。",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "title", "format", "filename", "purpose", "content"],
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "format": {
                                "type": "string",
                                "enum": ["pdf", "docx", "txt", "xlsx"],
                            },
                            "filename": {"type": "string"},
                            "purpose": {"type": "string"},
                            "content": {
                                "description": "完整檔案內容。pdf/docx/txt 使用 Markdown 風格純文字；xlsx 可用陣列或物件表示表格。",
                                "anyOf": [
                                    {"type": "string"},
                                    {"type": "array"},
                                    {"type": "object"},
                                ],
                            },
                        },
                    },
                },
                "references": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["source_name", "quote_or_summary", "used_for"],
                        "properties": {
                            "source_name": {"type": "string"},
                            "quote_or_summary": {"type": "string"},
                            "used_for": {"type": "string"},
                        },
                    },
                },
                "limitations": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "academic_integrity_notice": {"type": "string"},
                "human_review_checklist": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
    },
}


def build_user_prompt(
    assignment_text: str,
    course_materials: list[dict],
    assignment_files: list[dict],
) -> dict:
    parts = []
    images = []

    parts.append("## 本次作業輸入模式")
    input_modes = []
    if assignment_text and assignment_text.strip():
        input_modes.append("作業敘述文字")
    if assignment_files:
        input_modes.append("作業檔案")
    parts.append(f"使用者提供：{'、'.join(input_modes) if input_modes else '未提供作業輸入'}。請整合所有作業輸入來源。")

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
            if mat.get("image_data_url"):
                images.append({"filename": mat["filename"], "data_url": mat["image_data_url"]})
                parts.append("[圖片附件] 此檔案已附加至 AI 請求，請直接判讀圖片內容。")

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
            if f.get("image_data_url"):
                images.append({"filename": f["filename"], "data_url": f["image_data_url"]})
                parts.append("[圖片附件] 此檔案已附加至 AI 請求，請直接判讀圖片內容。")

    parts.append("\n---")
    parts.append("## 執行指令")
    parts.append("請根據以上所有資料，產生結構化的作業輔助草稿。")
    parts.append("1. 先判斷本次作業輸入模式，並明確摘要你理解到的作業要求。")
    parts.append("2. 如果是文字敘述模式，以文字敘述為主要需求，課程資料只作為補充參考。")
    parts.append("3. 如果是作業檔案模式，從檔案內容推斷作業需求，並標出無法判讀或需要使用者補充確認的部分。")
    parts.append("4. 先提供 `explanation` 講解，再在 `deliverables` 決定要產生哪些檔案與每份檔案內容。")
    parts.append("5. 若可用，請呼叫 `submit_assignment_result` 工具送出完整結果；若工具不可用，才嚴格按照系統提示詞的 JSON 格式輸出。")
    parts.append("6. `deliverables[].content` 必須是完整檔案內容，不可只寫大綱或請見說明。")
    parts.append("7. 全文必須使用 zh-TW 台灣正體中文文法、用語、詞彙與標點。")
    parts.append("8. 不要宣稱已送交外部平台；系統後端只會依工具參數或 JSON 結果產生下載檔。")

    return {"text": "\n".join(parts), "images": images}


def build_image_data_url(file_path: str, file_type: str) -> str | None:
    ext = file_type.lower().lstrip(".")
    mime_types = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    mime_type = mime_types.get(ext)
    if not mime_type:
        return None
    data = base64.b64encode(open(file_path, "rb").read()).decode("ascii")
    return f"data:{mime_type};base64,{data}"


def _build_user_message_content(user_prompt: str | dict):
    if isinstance(user_prompt, str):
        return user_prompt

    content = [{"type": "text", "text": str(user_prompt.get("text", ""))}]
    for image in user_prompt.get("images", []):
        if not isinstance(image, dict) or not image.get("data_url"):
            continue
        content.append({
            "type": "image_url",
            "image_url": {"url": image["data_url"]},
        })
    return content


def _strip_json_fence(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def _extract_json_object(content: str) -> str:
    content = _strip_json_fence(content)
    if content.startswith("{") and content.endswith("}"):
        return content

    start = content.find("{")
    if start < 0:
        return content

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start:index + 1]

    return content


def _load_json_object(content: str) -> dict:
    parsed = json.loads(_extract_json_object(content))
    if not isinstance(parsed, dict):
        raise ValueError("AI 回覆不是 JSON 物件")
    return parsed


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _reference_list(value) -> list[dict]:
    if not isinstance(value, list):
        return []

    references = []
    for item in value:
        if not isinstance(item, dict):
            continue
        references.append({
            "source_name": str(item.get("source_name") or "未標明來源"),
            "quote_or_summary": str(item.get("quote_or_summary") or ""),
            "used_for": str(item.get("used_for") or ""),
        })
    return references


def _normalize_ai_output(data: dict, generation_method: str) -> dict:
    structured = {
        "title": str(data.get("title") or "AI 輔助結果"),
        "assignment_summary": str(data.get("assignment_summary") or ""),
        "explanation": str(data.get("explanation") or ""),
        "requirements_breakdown": _string_list(data.get("requirements_breakdown")),
        "answer_outline": _string_list(data.get("answer_outline")),
        "generated_draft": str(data.get("generated_draft") or ""),
        "deliverables": data.get("deliverables") if isinstance(data.get("deliverables"), list) else [],
        "references": _reference_list(data.get("references")),
        "limitations": _string_list(data.get("limitations")),
        "generation_method": generation_method,
    }

    if data.get("academic_integrity_notice"):
        structured["academic_integrity_notice"] = str(data["academic_integrity_notice"])
    if isinstance(data.get("human_review_checklist"), list):
        structured["human_review_checklist"] = _string_list(data["human_review_checklist"])

    return structured


def _raw_output_fallback(content: str) -> dict:
    content = content.strip() or "AI 沒有回傳可顯示的內容。"
    return {
        "title": "AI 輔助結果",
        "assignment_summary": "",
        "explanation": "AI 未能以工具或結構化 JSON 格式回覆，以下保留原始輸出供畫面顯示，並建立 TXT 備份檔供下載。",
        "requirements_breakdown": [],
        "answer_outline": [],
        "generated_draft": content,
        "deliverables": [
            {
                "id": "raw_ai_output",
                "title": "AI 原始輸出備份",
                "format": "txt",
                "filename": "ai_raw_output.txt",
                "purpose": "保留 AI 原始回覆內容，避免本次結果沒有任何可下載檔案。",
                "content": content,
            }
        ],
        "references": [],
        "limitations": ["AI 未能使用指定工具或 JSON 格式回覆，因此此檔案是原始輸出備份。"],
        "generation_method": "raw_fallback",
    }


def _with_tools(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload["tools"] = [ASSIGNMENT_RESULT_TOOL]
    payload["tool_choice"] = {
        "type": "function",
        "function": {"name": "submit_assignment_result"},
    }
    return payload


def _extract_tool_result(message: dict) -> dict | None:
    function_call = message.get("function_call")
    if isinstance(function_call, dict) and function_call.get("name") == "submit_assignment_result":
        arguments = function_call.get("arguments") or "{}"
        parsed = arguments if isinstance(arguments, dict) else _load_json_object(str(arguments))
        return _normalize_ai_output(parsed, "function_call")

    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return None

    for tool_call in tool_calls:
        function = tool_call.get("function") if isinstance(tool_call, dict) else None
        if not isinstance(function, dict):
            continue
        if function.get("name") != "submit_assignment_result":
            continue

        arguments = function.get("arguments") or "{}"
        parsed = arguments if isinstance(arguments, dict) else _load_json_object(str(arguments))
        return _normalize_ai_output(parsed, "tool_call")

    return None


def _parse_chat_completion(data: dict) -> dict:
    message = data["choices"][0]["message"]

    try:
        tool_result = _extract_tool_result(message)
        if tool_result:
            return tool_result
    except (json.JSONDecodeError, ValueError):
        pass

    content = message.get("content") or ""
    if isinstance(content, list):
        content = "\n".join(
            str(part.get("text", ""))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    content = str(content).strip()

    try:
        return _normalize_ai_output(_load_json_object(content), "json")
    except (json.JSONDecodeError, ValueError):
        return _raw_output_fallback(content)


def _looks_like_unsupported_tools_error(response: httpx.Response) -> bool:
    if response.status_code not in {400, 404, 422}:
        return False

    body = response.text.lower()
    return any(
        keyword in body
        for keyword in (
            "tool",
            "tool_choice",
            "function",
            "functions",
            "unsupported",
            "unrecognized",
            "unknown parameter",
        )
    )


async def call_ai_api(system_prompt: str, user_prompt: str | dict, config: dict) -> dict:
    base_url = config["base_url"].rstrip("/")
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": _build_user_message_content(user_prompt)},
        ],
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=_with_tools(payload),
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if _looks_like_unsupported_tools_error(response):
                response = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as fallback_exc:
                    body = response.text[:1000]
                    raise RuntimeError(
                        f"AI API 回傳 {response.status_code}：{body or fallback_exc.response.reason_phrase}"
                    ) from fallback_exc
            else:
                body = response.text[:1000]
                raise RuntimeError(
                    f"AI API 回傳 {response.status_code}：{body or exc.response.reason_phrase}"
                ) from exc
        data = response.json()

    return _parse_chat_completion(data)


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
