from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.models import Limitation, Reference, UploadedFile
from app.services.progress_service import write_event
from app.tools._helpers import ToolContext, ToolError


def tool_log_progress(ctx: ToolContext, args: dict) -> dict[str, Any]:
    stage = args.get("stage")
    message = args.get("message")
    if not isinstance(stage, str) or not stage.strip():
        raise ToolError("invalid_argument", "stage 必填")
    if not isinstance(message, str) or not message.strip():
        raise ToolError("invalid_argument", "message 必填")
    if len(message) > 200:
        message = message[:200]

    event = write_event(
        ctx.db,
        ctx.task.id,
        event_type="agent_log",
        message=message,
        detail={"stage": stage, "iteration": ctx.iteration},
    )
    return {"event_id": event.id}


def tool_add_reference(ctx: ToolContext, args: dict) -> dict[str, Any]:
    source_name = args.get("source_name")
    quote = args.get("quote_or_summary")
    used_for = args.get("used_for")
    if not isinstance(source_name, str) or not source_name.strip():
        raise ToolError("invalid_argument", "source_name 必填")
    if quote is not None and not isinstance(quote, str):
        raise ToolError("invalid_argument", "quote_or_summary 需為字串")
    if used_for is not None and not isinstance(used_for, str):
        raise ToolError("invalid_argument", "used_for 需為字串")
    if quote and len(quote) > 500:
        quote = quote[:500]
    if used_for and len(used_for) > 200:
        used_for = used_for[:200]

    # 驗證 source 對應上傳檔案，否則必須標明為「Agent 知識」
    if not source_name.startswith("Agent 知識"):
        stmt = select(UploadedFile).where(
            UploadedFile.task_id == ctx.task.id,
            UploadedFile.original_filename == source_name,
        )
        if ctx.db.execute(stmt).first() is None:
            raise ToolError(
                "invalid_argument",
                f"source_name '{source_name}' 不在本任務上傳檔案中；若要引用模型知識請使用「Agent 知識」開頭。",
            )

    ref = Reference(
        task_id=ctx.task.id,
        source_name=source_name,
        quote_or_summary=quote,
        used_for=used_for,
    )
    ctx.db.add(ref)
    ctx.db.flush()
    return {"reference_id": ref.id}


def tool_add_limitation(ctx: ToolContext, args: dict) -> dict[str, Any]:
    text = args.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ToolError("invalid_argument", "text 必填")
    if len(text) > 300:
        text = text[:300]
    lim = Limitation(task_id=ctx.task.id, text=text)
    ctx.db.add(lim)
    ctx.db.flush()
    return {"limitation_id": lim.id}
