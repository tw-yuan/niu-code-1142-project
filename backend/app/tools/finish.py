from __future__ import annotations

from typing import Any

from app.tools._helpers import ToolContext, ToolError


def tool_finish(ctx: ToolContext, args: dict) -> dict[str, Any]:
    title = args.get("title")
    summary = args.get("assignment_summary")
    explanation = args.get("explanation")

    if not isinstance(title, str) or not title.strip():
        raise ToolError("invalid_argument", "title 必填")
    if not isinstance(summary, str) or not summary.strip():
        raise ToolError("invalid_argument", "assignment_summary 必填")
    if not isinstance(explanation, str) or not explanation.strip():
        raise ToolError("invalid_argument", "explanation 必填")

    if len(title) > 100:
        title = title[:100]
    if len(summary) > 500:
        summary = summary[:500]
    if len(explanation) > 3000:
        explanation = explanation[:3000]

    ctx.task.agent_title = title
    ctx.task.agent_assignment_summary = summary
    ctx.task.agent_explanation = explanation
    ctx.db.flush()
    return {"ok": True}
