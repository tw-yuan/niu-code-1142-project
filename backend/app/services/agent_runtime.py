from __future__ import annotations

import json
import logging
import time
from typing import Any

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import AgentToolCall, GeneratedFile, Task
from app.services.progress_service import write_event
from app.services.system_setting_service import get_runtime_config
from app.tools._helpers import ToolContext, ToolError, truncate_for_llm
from app.tools.registry import build_tool_catalog, dispatch

logger = logging.getLogger(__name__)


MAX_CONSECUTIVE_SAME_TOOL_ERRORS = 5
MAX_BARE_TEXT_RESPONSES = 5
ARGS_PERSIST_CHAR_CAP = 4000
RESULT_PERSIST_CHAR_CAP = 4000


class AgentRuntimeError(Exception):
    pass


def run_task_blocking(task_id: str) -> None:
    """Entry point intended to be invoked via FastAPI BackgroundTasks."""
    db: Session = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            logger.warning("agent_runtime: task %s not found", task_id)
            return
        if task.status not in {"pending", "failed"}:
            logger.info("agent_runtime: task %s already in status %s; skipping", task_id, task.status)
            return
        try:
            _run(db, task)
        except Exception as exc:  # noqa: BLE001
            logger.exception("agent_runtime: unexpected failure for %s", task_id)
            task = db.get(Task, task_id)
            if task is not None:
                task.status = "failed"
                task.error_message = f"{type(exc).__name__}: {exc}"[:1000]
                write_event(
                    db,
                    task.id,
                    event_type="error",
                    message="Agent 執行時發生未預期錯誤",
                    detail={"error": task.error_message},
                )
                db.commit()
    finally:
        db.close()


def _run(db: Session, task: Task) -> None:
    settings = get_settings()
    config = get_runtime_config(db)

    if not settings.openai_compatible_api_key:
        task.status = "failed"
        task.error_message = "尚未設定 OPENAI_COMPATIBLE_API_KEY"
        write_event(
            db,
            task.id,
            event_type="error",
            message="尚未設定 API Key，無法呼叫 AI",
        )
        db.commit()
        return

    task.status = "processing"
    task.model_name = config["model_name"]
    db.flush()
    write_event(
        db,
        task.id,
        event_type="agent_start",
        message="Agent 啟動",
        detail={"model": config["model_name"], "max_iterations": config["max_iterations"]},
    )
    db.commit()

    client = OpenAI(
        api_key=settings.openai_compatible_api_key,
        base_url=config["base_url"],
    )

    tools = build_tool_catalog(db)
    user_prompt = _build_user_prompt(task)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": config["system_prompt"]},
        {"role": "user", "content": user_prompt},
    ]

    consecutive_tool_errors: dict[str, int] = {}
    bare_text_responses = 0
    finished = False

    for iteration in range(1, config["max_iterations"] + 1):
        task.iterations_used = iteration
        db.flush()
        db.commit()

        try:
            completion = _call_llm(
                client=client,
                model=config["model_name"],
                messages=messages,
                tools=tools,
            )
        except (APITimeoutError, APIConnectionError, RateLimitError, APIError) as exc:
            logger.warning("agent_runtime: LLM call failed iter=%s err=%s", iteration, exc)
            task.status = "failed"
            task.error_message = f"LLM 呼叫失敗：{type(exc).__name__}"
            write_event(
                db,
                task.id,
                event_type="error",
                message="呼叫 LLM 失敗",
                detail={"error": str(exc)[:300]},
            )
            db.commit()
            return

        choice = completion.choices[0]
        msg = choice.message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            bare_text_responses += 1
            content = msg.content or ""
            write_event(
                db,
                task.id,
                event_type="agent_text",
                message="Agent 回了純文字，提醒它使用 tools",
                detail={"snippet": content[:300]},
            )
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "你回了純文字。請改用提供的 tools 來執行動作；"
                        "若已完成所有寫檔工作，請呼叫 finish(title, assignment_summary, explanation) 結束。"
                    ),
                }
            )
            db.commit()
            if bare_text_responses >= MAX_BARE_TEXT_RESPONSES:
                task.status = "failed"
                task.error_message = "Agent 連續多輪未呼叫 tools"
                write_event(
                    db,
                    task.id,
                    event_type="error",
                    message="Agent 無法正確使用 tools，已中止",
                )
                db.commit()
                return
            continue

        bare_text_responses = 0

        # Append assistant message (must include tool_calls for tool turn to work)
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.function.name, "arguments": c.function.arguments},
                    }
                    for c in tool_calls
                ],
            }
        )

        for call in tool_calls:
            tool_name = call.function.name or "(unknown)"
            args_raw = call.function.arguments or "{}"
            args: dict[str, Any]
            try:
                args = json.loads(args_raw) if args_raw else {}
                if not isinstance(args, dict):
                    raise ValueError("arguments must be a JSON object")
            except (ValueError, TypeError) as exc:
                args = {}
                err_payload = {"error": {"code": "invalid_argument", "message": f"無法解析 arguments：{exc}"}}
                _persist_tool_call_record(
                    db,
                    task,
                    iteration,
                    tool_name,
                    args_raw_obj=args,
                    result=err_payload,
                    status="error",
                    error_message=str(exc),
                    duration_ms=0,
                )
                consecutive_tool_errors[tool_name] = consecutive_tool_errors.get(tool_name, 0) + 1
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(err_payload, ensure_ascii=False),
                    }
                )
                db.commit()
                continue

            if finished:
                ignored_payload = {"ignored": True, "reason": "Agent 已呼叫 finish，本輪 tool call 不執行"}
                _persist_tool_call_record(
                    db,
                    task,
                    iteration,
                    tool_name,
                    args_raw_obj=args,
                    result=ignored_payload,
                    status="ignored",
                    error_message=None,
                    duration_ms=0,
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(ignored_payload, ensure_ascii=False),
                    }
                )
                db.commit()
                continue

            t0 = time.perf_counter()
            ctx = ToolContext(
                db=db,
                task=task,
                iteration=iteration,
                generated_count=_count_generated(db, task.id),
            )
            try:
                result = dispatch(tool_name, ctx, args)
                status_ = "success"
                err_msg = None
                consecutive_tool_errors[tool_name] = 0
            except ToolError as exc:
                result = exc.to_dict()
                status_ = "error"
                err_msg = exc.message
                consecutive_tool_errors[tool_name] = consecutive_tool_errors.get(tool_name, 0) + 1
            except Exception as exc:  # noqa: BLE001
                logger.exception("tool %s blew up", tool_name)
                result = {
                    "error": {
                        "code": "internal_error",
                        "message": f"tool 內部錯誤：{type(exc).__name__}",
                    }
                }
                status_ = "error"
                err_msg = str(exc)
                consecutive_tool_errors[tool_name] = consecutive_tool_errors.get(tool_name, 0) + 1

            elapsed_ms = int((time.perf_counter() - t0) * 1000)

            tool_call_row = _persist_tool_call_record(
                db,
                task,
                iteration,
                tool_name,
                args_raw_obj=args,
                result=result,
                status=status_,
                error_message=err_msg,
                duration_ms=elapsed_ms,
            )

            if status_ == "success" and tool_name.startswith("write_"):
                _attach_generated_file_to_tool_call(
                    db, task.id, tool_call_row.id, result.get("generated_file_id")
                )

            if status_ == "success" and tool_name == "finish":
                finished = True
                task.status = "completed"
                task.error_message = None
                write_event(
                    db,
                    task.id,
                    event_type="agent_finish",
                    message="Agent 完成任務",
                    detail={"iteration": iteration},
                )

            truncated_result = truncate_for_llm(result, RESULT_PERSIST_CHAR_CAP)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(truncated_result, ensure_ascii=False),
                }
            )
            db.commit()

            if consecutive_tool_errors.get(tool_name, 0) >= MAX_CONSECUTIVE_SAME_TOOL_ERRORS:
                # Inject a reminder to change strategy
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"tool {tool_name} 連續 {MAX_CONSECUTIVE_SAME_TOOL_ERRORS} 次失敗，"
                            "請改用不同 tool 或先呼叫 add_limitation 說明後再 finish。"
                        ),
                    }
                )
                consecutive_tool_errors[tool_name] = 0

            if finished:
                break

        if finished:
            db.commit()
            return

    # max_iterations reached without finish
    task.status = "failed"
    task.error_message = "已達 max_iterations，Agent 未呼叫 finish"
    write_event(
        db,
        task.id,
        event_type="error",
        message="Agent 達到迭代上限仍未完成，已保留已寫出的檔案",
        detail={"max_iterations": config["max_iterations"]},
    )
    db.commit()


def _build_user_prompt(task: Task) -> str:
    parts: list[str] = [
        f"任務 ID：{task.id}",
        "",
        "請依照系統提示詞的工作流程開始。第一步建議先呼叫 list_inputs 看看有哪些檔案。",
        "",
    ]
    if task.assignment_text:
        parts.append("使用者輸入的作業敘述：")
        parts.append(task.assignment_text)
        parts.append("")
    else:
        parts.append("使用者未提供文字作業敘述，請依上傳的作業檔案內容判斷需求。")
        parts.append("")
    return "\n".join(parts)


def _call_llm(
    client: OpenAI,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
):
    # 1 retry on transient failures (caller handles surfacing)
    last_exc: Exception | None = None
    for attempt in range(2):
        try:
            return client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            last_exc = exc
            time.sleep(1.5 * (attempt + 1))
        except APIError as exc:
            # Some APIError variants are not retryable; only retry once for 5xx-style
            last_exc = exc
            time.sleep(1.0)
    assert last_exc is not None
    raise last_exc


def _persist_tool_call_record(
    db: Session,
    task: Task,
    iteration: int,
    tool_name: str,
    args_raw_obj: dict,
    result: dict,
    status: str,
    error_message: str | None,
    duration_ms: int,
) -> AgentToolCall:
    args_payload = truncate_for_llm(args_raw_obj, ARGS_PERSIST_CHAR_CAP)
    result_payload = truncate_for_llm(result, RESULT_PERSIST_CHAR_CAP)
    row = AgentToolCall(
        task_id=task.id,
        iteration=iteration,
        tool_name=tool_name,
        arguments_json=_safe_jsonable(args_payload),
        result_json=_safe_jsonable(result_payload),
        status=status,
        error_message=(error_message or "")[:1000] if error_message else None,
        duration_ms=duration_ms,
    )
    db.add(row)
    db.flush()
    return row


def _attach_generated_file_to_tool_call(
    db: Session,
    task_id: str,
    tool_call_id: str,
    generated_file_id: str | None,
) -> None:
    if not generated_file_id:
        return
    gf = db.get(GeneratedFile, generated_file_id)
    if gf is None or gf.task_id != task_id:
        return
    gf.tool_call_id = tool_call_id
    db.flush()


def _count_generated(db: Session, task_id: str) -> int:
    stmt = select(func.count(GeneratedFile.id)).where(GeneratedFile.task_id == task_id)
    return int(db.execute(stmt).scalar() or 0)


def _safe_jsonable(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except (TypeError, ValueError):
        return {"value": str(value)[:1000]}
