from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models import Task


MAX_TOOL_RESULT_CHARS = 4000  # truncated payload sent back into LLM
ALLOWED_WRITE_EXTENSIONS = {".txt", ".md", ".docx", ".pdf", ".xlsx"}
ACADEMIC_INTEGRITY_FOOTER_TEXT = (
    "\n\n---\n"
    "【學術誠信提醒】\n"
    "本文件由 AI Agent 自動生成，僅作為學業輔助與草稿用途，請勿直接繳交。\n"
    "使用前請務必：\n"
    "- 自行審閱內容、確認資料正確性與引用是否得當。\n"
    "- 補充個人觀點與課程實際要求。\n"
    "- 遵守任課老師與所屬機構的學術誠信規範。\n"
    "本系統不會替你送交作業，也不協助規避 AI / 抄襲偵測。\n"
)


@dataclass
class ToolContext:
    db: Session
    task: Task
    iteration: int
    generated_count: int


class ToolError(Exception):
    """Raised by tool implementations with a structured payload."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
            }
        }


def truncate_for_llm(payload: Any, limit: int = MAX_TOOL_RESULT_CHARS) -> Any:
    """Serialize and truncate a payload so it does not blow up the LLM context."""
    try:
        encoded = json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        encoded = json.dumps({"value": str(payload)}, ensure_ascii=False)
    if len(encoded) <= limit:
        return payload
    truncated_str = encoded[:limit]
    return {"_truncated": True, "_chars": len(encoded), "snippet": truncated_str}


def academic_integrity_footer_markdown() -> str:
    return ACADEMIC_INTEGRITY_FOOTER_TEXT
