from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.models import UploadedFile
from app.tools._helpers import ToolContext, ToolError


MAX_READ_CHARS_DEFAULT = 4000
MAX_READ_CHARS_HARD_CAP = 8000
MAX_TABLE_ROWS_RETURN = 200
MAX_TABLE_COLS_RETURN = 30
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB raw — about 6.7 MB once base64-encoded
IMAGE_MIME = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


def tool_list_inputs(ctx: ToolContext, args: dict) -> dict[str, Any]:
    del args
    stmt = (
        select(UploadedFile)
        .where(UploadedFile.task_id == ctx.task.id)
        .order_by(UploadedFile.created_at.asc())
    )
    rows = ctx.db.execute(stmt).scalars().all()
    return {
        "files": [
            {
                "file_id": f.id,
                "category": f.file_category,
                "filename": f.original_filename,
                "file_type": f.file_type,
                "size_bytes": f.file_size,
                "parse_status": f.parse_status,
                "summary": f.summary or "",
            }
            for f in rows
        ]
    }


def tool_read_input_text(ctx: ToolContext, args: dict) -> dict[str, Any]:
    file_id = args.get("file_id")
    if not isinstance(file_id, str) or not file_id:
        raise ToolError("invalid_argument", "file_id 必填且需為字串")

    max_chars = args.get("max_chars", MAX_READ_CHARS_DEFAULT)
    if not isinstance(max_chars, int):
        try:
            max_chars = int(max_chars)
        except (TypeError, ValueError):
            max_chars = MAX_READ_CHARS_DEFAULT
    max_chars = max(200, min(max_chars, MAX_READ_CHARS_HARD_CAP))

    f = ctx.db.get(UploadedFile, file_id)
    if f is None or f.task_id != ctx.task.id:
        raise ToolError("file_not_found", "找不到此 file_id 或不屬於本任務")
    if f.parsed_text is None:
        raise ToolError("not_parsed", f"檔案 {f.original_filename} 沒有可讀的文字內容")

    text = f.parsed_text
    truncated = len(text) > max_chars
    return {
        "file_id": f.id,
        "filename": f.original_filename,
        "text": text[:max_chars],
        "truncated": truncated,
    }


def tool_read_input_image(ctx: ToolContext, args: dict) -> dict[str, Any]:
    file_id = args.get("file_id")
    if not isinstance(file_id, str) or not file_id:
        raise ToolError("invalid_argument", "file_id 必填且需為字串")

    f = ctx.db.get(UploadedFile, file_id)
    if f is None or f.task_id != ctx.task.id:
        raise ToolError("file_not_found", "找不到此 file_id 或不屬於本任務")

    file_type = (f.file_type or "").lower()
    if file_type not in IMAGE_MIME:
        raise ToolError(
            "unsupported_for_image",
            f"檔案 {f.original_filename} 不是支援的圖片格式（支援 png/jpg/webp）",
        )

    path = Path(f.stored_path)
    if not path.exists():
        raise ToolError("file_not_found", f"檔案 {f.original_filename} 已不在磁碟上")

    size = path.stat().st_size
    if size > MAX_IMAGE_BYTES:
        raise ToolError(
            "size_limit_exceeded",
            f"圖片 {f.original_filename} 大小 {size} 超過上限 {MAX_IMAGE_BYTES} bytes（{MAX_IMAGE_BYTES // (1024 * 1024)}MB）",
        )

    mime = IMAGE_MIME[file_type]
    raw = path.read_bytes()
    data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"

    # The runtime extracts these private fields, then strips them before persisting
    # the result row and before sending the tool message back to the LLM.
    return {
        "loaded": True,
        "file_id": f.id,
        "filename": f.original_filename,
        "mime": mime,
        "size_bytes": size,
        "_inject_image_data_url": data_url,
        "_inject_image_filename": f.original_filename,
    }


def tool_read_input_table(ctx: ToolContext, args: dict) -> dict[str, Any]:
    file_id = args.get("file_id")
    if not isinstance(file_id, str) or not file_id:
        raise ToolError("invalid_argument", "file_id 必填且需為字串")
    target_sheet = args.get("sheet")

    f = ctx.db.get(UploadedFile, file_id)
    if f is None or f.task_id != ctx.task.id:
        raise ToolError("file_not_found", "找不到此 file_id 或不屬於本任務")
    if not f.parsed_table_json or not isinstance(f.parsed_table_json, dict):
        raise ToolError("not_parsed", f"檔案 {f.original_filename} 沒有可讀的表格資料")

    raw_sheets = f.parsed_table_json.get("sheets") or []
    if isinstance(target_sheet, str) and target_sheet:
        raw_sheets = [s for s in raw_sheets if s.get("name") == target_sheet]
        if not raw_sheets:
            raise ToolError("invalid_argument", f"找不到 sheet：{target_sheet}")

    out_sheets = []
    for s in raw_sheets:
        cols = list(s.get("columns") or [])[:MAX_TABLE_COLS_RETURN]
        rows = [list(r)[:MAX_TABLE_COLS_RETURN] for r in (s.get("rows") or [])][:MAX_TABLE_ROWS_RETURN]
        truncated = bool(s.get("truncated")) or len(s.get("rows") or []) > MAX_TABLE_ROWS_RETURN
        out_sheets.append(
            {
                "name": s.get("name", "sheet"),
                "columns": cols,
                "rows": rows,
                "row_count": len(s.get("rows") or []),
                "truncated": truncated,
            }
        )

    return {"sheets": out_sheets}
