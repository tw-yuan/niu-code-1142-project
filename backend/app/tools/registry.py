from __future__ import annotations

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.services.system_setting_service import get_enabled_tools
from app.tools._helpers import ToolContext, ToolError
from app.tools.annotate import (
    tool_add_limitation,
    tool_add_reference,
    tool_log_progress,
)
from app.tools.finish import tool_finish
from app.tools.read_inputs import (
    tool_list_inputs,
    tool_read_input_table,
    tool_read_input_text,
)
from app.tools.write_files import (
    tool_write_docx_file,
    tool_write_pdf_file,
    tool_write_text_file,
    tool_write_xlsx_file,
)


ToolFn = Callable[[ToolContext, dict], dict[str, Any]]


TOOL_IMPLEMENTATIONS: dict[str, ToolFn] = {
    "list_inputs": tool_list_inputs,
    "read_input_text": tool_read_input_text,
    "read_input_table": tool_read_input_table,
    "log_progress": tool_log_progress,
    "add_reference": tool_add_reference,
    "add_limitation": tool_add_limitation,
    "write_text_file": tool_write_text_file,
    "write_docx_file": tool_write_docx_file,
    "write_pdf_file": tool_write_pdf_file,
    "write_xlsx_file": tool_write_xlsx_file,
    "finish": tool_finish,
}


def build_tool_catalog(db: Session) -> list[dict[str, Any]]:
    """Build the OpenAI-format tool catalog filtered by Admin enable/disable settings."""
    enabled = set(get_enabled_tools(db))
    return [t for t in _ALL_SCHEMAS if t["function"]["name"] in enabled]


def dispatch(name: str, ctx: ToolContext, args: dict) -> dict[str, Any]:
    fn = TOOL_IMPLEMENTATIONS.get(name)
    if fn is None:
        raise ToolError("tool_disabled", f"未知或停用的 tool：{name}")
    return fn(ctx, args or {})


_ALL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_inputs",
            "description": "列出本任務所有上傳檔案的 metadata 與解析狀態。無參數。",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_input_text",
            "description": "讀取某個上傳檔案的解析文字內容；自動截斷至 max_chars。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "list_inputs 回傳的 file_id"},
                    "max_chars": {
                        "type": "integer",
                        "description": "想讀取的最大字數，預設 4000，上限 8000",
                        "minimum": 200,
                        "maximum": 8000,
                    },
                },
                "required": ["file_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_input_table",
            "description": "讀取已解析的表格資料（XLSX / CSV）。可選 sheet 名稱。",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "sheet": {"type": "string", "description": "選填，未填回傳所有 sheets"},
                },
                "required": ["file_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_progress",
            "description": "寫一筆進度訊息給前端 SSE。每階段呼叫一次即可。",
            "parameters": {
                "type": "object",
                "properties": {
                    "stage": {
                        "type": "string",
                        "description": "階段標籤，例如 analyzing / drafting / writing_docx",
                    },
                    "message": {
                        "type": "string",
                        "description": "給使用者看的訊息（200 字內）",
                    },
                },
                "required": ["stage", "message"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_reference",
            "description": "新增一條引用來源。source_name 必須對應 list_inputs 中的檔名，或以「Agent 知識」開頭。",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_name": {"type": "string"},
                    "quote_or_summary": {"type": "string", "description": "引文或摘要（500 字內）"},
                    "used_for": {"type": "string", "description": "用在輸出哪一部分（200 字內）"},
                },
                "required": ["source_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_limitation",
            "description": "新增一條限制或缺資料說明（300 字內）。",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_text_file",
            "description": "寫出純文字檔（.txt 或 .md）。會自動附加學術誠信提醒。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "副檔名 .txt 或 .md"},
                    "purpose": {"type": "string", "description": "這份檔案的用途（200 字內）"},
                    "content": {"type": "string", "description": "完整內容（30000 字內）"},
                },
                "required": ["filename", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_docx_file",
            "description": "寫出 DOCX。Agent 提供結構化 blocks，tool 層組裝。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": ".docx 結尾"},
                    "purpose": {"type": "string"},
                    "blocks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "heading",
                                        "paragraph",
                                        "bullet_list",
                                        "numbered_list",
                                        "table",
                                    ],
                                },
                                "level": {"type": "integer", "minimum": 1, "maximum": 6},
                                "text": {"type": "string"},
                                "items": {"type": "array", "items": {"type": "string"}},
                                "columns": {"type": "array", "items": {"type": "string"}},
                                "rows": {
                                    "type": "array",
                                    "items": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                            "required": ["type"],
                        },
                    },
                },
                "required": ["filename", "blocks"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_pdf_file",
            "description": "寫出 PDF。Blocks 結構同 write_docx_file。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": ".pdf 結尾"},
                    "purpose": {"type": "string"},
                    "blocks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "heading",
                                        "paragraph",
                                        "bullet_list",
                                        "numbered_list",
                                        "table",
                                    ],
                                },
                                "level": {"type": "integer", "minimum": 1, "maximum": 6},
                                "text": {"type": "string"},
                                "items": {"type": "array", "items": {"type": "string"}},
                                "columns": {"type": "array", "items": {"type": "string"}},
                                "rows": {
                                    "type": "array",
                                    "items": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                            "required": ["type"],
                        },
                    },
                },
                "required": ["filename", "blocks"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_xlsx_file",
            "description": "寫出 XLSX，多 sheet。",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": ".xlsx 結尾"},
                    "purpose": {"type": "string"},
                    "sheets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "columns": {"type": "array", "items": {"type": "string"}},
                                "rows": {
                                    "type": "array",
                                    "items": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                            "required": ["name"],
                        },
                    },
                },
                "required": ["filename", "sheets"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "結束 Agent loop，提供標題、作業摘要與最終講解。finish 之後的 tool call 會被忽略。",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "100 字內"},
                    "assignment_summary": {"type": "string", "description": "500 字內"},
                    "explanation": {"type": "string", "description": "給使用者看的講解，3000 字內"},
                },
                "required": ["title", "assignment_summary", "explanation"],
                "additionalProperties": False,
            },
        },
    },
]
