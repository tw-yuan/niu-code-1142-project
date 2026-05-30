from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import SystemSetting, SystemSettingHistory


DEFAULT_SYSTEM_PROMPT = (
    "你是「AI 課業輔助與作業草稿生成系統」中的 Assignment Drafting Agent。\n"
    "請務必使用台灣繁體中文（zh-TW）與台灣常用詞彙、標點，禁止使用簡體字或中國大陸用語。\n"
    "\n"
    "本系統定位是學業輔助與草稿生成，不是替代學生提交作業的代寫工具。\n"
    "- 不協助規避抄襲/AI 偵測、不自動送交、不宣稱輸出可直接交。\n"
    "- 任何引用必須來自 list_inputs 中存在的檔名，或註明為 Agent 知識。\n"
    "- 缺資料時用 add_limitation 註記，不要硬編內容。\n"
    "\n"
    "工作流程：\n"
    "1) 先呼叫 list_inputs 看看本任務有哪些檔案。\n"
    "2) 對你需要的檔案呼叫 read_input_text 或 read_input_table 讀內容。\n"
    "3) 規劃要交付什麼，使用 log_progress 階段性回報；可以一邊累積 add_reference / add_limitation。\n"
    "4) 用 write_text_file / write_docx_file / write_pdf_file / write_xlsx_file 寫出最終檔案。\n"
    "   - 純文字草稿 → write_text_file（.txt 或 .md）\n"
    "   - 報告型內容 → write_docx_file（含 heading / paragraph / bullet_list / table blocks）\n"
    "   - 表格 / 數據作業 → write_xlsx_file\n"
    "   - 接近繳交版的固定版型 → write_pdf_file\n"
    "5) 最後必須呼叫 finish(title, assignment_summary, explanation) 結束。\n"
    "\n"
    "其他規則：\n"
    "- 達到迭代上限會被強制中止，請務必在用完額度前呼叫 finish。\n"
    "- 同一個 tool 連續錯 5 次以上請改用其他策略或 add_limitation 後 finish。\n"
    "- 不要在 tool 參數中放 API Key、密碼或其他使用者敏感資料。\n"
    "- 文件的學術誠信提醒與人工確認清單會由 tool 層自動附加，請專心寫實際內容。"
)


KEY_SYSTEM_PROMPT = "system_prompt"
KEY_MODEL_NAME = "model_name"
KEY_BASE_URL = "base_url"
KEY_TEMPERATURE = "temperature"
KEY_MAX_OUTPUT_TOKENS = "max_output_tokens"
KEY_MAX_ITERATIONS = "max_iterations"
KEY_MAX_FILE_SIZE_MB = "max_file_size_mb"
KEY_MAX_FILES_PER_TASK = "max_files_per_task"
KEY_DISABLED_TOOLS = "disabled_tools"

ALL_TOOL_NAMES = (
    "list_inputs",
    "read_input_text",
    "read_input_table",
    "log_progress",
    "add_reference",
    "add_limitation",
    "write_text_file",
    "write_docx_file",
    "write_pdf_file",
    "write_xlsx_file",
    "finish",
)
NEVER_DISABLE_TOOLS = {"finish"}


def _get_raw(db: Session, key: str) -> SystemSetting | None:
    stmt = select(SystemSetting).where(SystemSetting.key == key)
    return db.execute(stmt).scalar_one_or_none()


def get_str(db: Session, key: str, default: str) -> str:
    s = _get_raw(db, key)
    if s is None or s.value is None:
        return default
    return s.value


def get_int(db: Session, key: str, default: int) -> int:
    s = _get_raw(db, key)
    if s is None or s.value is None:
        return default
    try:
        return int(s.value)
    except (TypeError, ValueError):
        return default


def get_float(db: Session, key: str, default: float) -> float:
    s = _get_raw(db, key)
    if s is None or s.value is None:
        return default
    try:
        return float(s.value)
    except (TypeError, ValueError):
        return default


def get_disabled_tools(db: Session) -> set[str]:
    raw = get_str(db, KEY_DISABLED_TOOLS, "")
    if not raw:
        return set()
    return {t.strip() for t in raw.split(",") if t.strip() and t.strip() not in NEVER_DISABLE_TOOLS}


def get_enabled_tools(db: Session) -> list[str]:
    disabled = get_disabled_tools(db)
    return [name for name in ALL_TOOL_NAMES if name not in disabled]


def get_runtime_config(db: Session) -> dict[str, Any]:
    settings = get_settings()
    return {
        "system_prompt": get_str(db, KEY_SYSTEM_PROMPT, DEFAULT_SYSTEM_PROMPT),
        "model_name": get_str(db, KEY_MODEL_NAME, settings.openai_compatible_model),
        "base_url": get_str(db, KEY_BASE_URL, settings.openai_compatible_base_url),
        "temperature": get_float(db, KEY_TEMPERATURE, 0.3),
        "max_output_tokens": get_int(db, KEY_MAX_OUTPUT_TOKENS, 4096),
        "max_iterations": get_int(db, KEY_MAX_ITERATIONS, 20),
        "max_file_size_mb": get_int(db, KEY_MAX_FILE_SIZE_MB, settings.max_file_size_mb),
        "max_files_per_task": get_int(db, KEY_MAX_FILES_PER_TASK, 8),
        "disabled_tools": sorted(get_disabled_tools(db)),
    }


def set_value(
    db: Session,
    key: str,
    new_value: str,
    updated_by: str | None,
) -> SystemSetting:
    s = _get_raw(db, key)
    old_value = s.value if s else None
    if s is None:
        s = SystemSetting(key=key, value=new_value, updated_by=updated_by)
        db.add(s)
        db.flush()
    else:
        s.value = new_value
        s.updated_by = updated_by

    history = SystemSettingHistory(
        setting_id=s.id,
        key=key,
        old_value=old_value,
        new_value=new_value,
        updated_by=updated_by,
    )
    db.add(history)
    db.flush()
    return s
