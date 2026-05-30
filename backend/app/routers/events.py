from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.deps import get_current_session
from app.services.auth_service import AuthResult, resolve_session
from app.services.progress_service import list_events, serialize, subscribe, unsubscribe
from app.services.task_service import get_task_for_user
from app.utils.security import SESSION_COOKIE_NAME, verify_session_cookie

router = APIRouter(prefix="/api/tasks", tags=["tasks-events"])


HEARTBEAT_INTERVAL = 15.0


@router.get("/{task_id}/events")
async def stream_events(
    task_id: str,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    task = get_task_for_user(db, task_id, auth.user_id, auth.role)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到任務")

    # Use a captured signed cookie value to re-validate inside the generator (its own DB session).
    signed_cookie = session_cookie

    async def event_gen() -> AsyncIterator[bytes]:
        own_db = SessionLocal()
        try:
            # Re-validate session inside generator scope (request lifespan ends quickly for SSE).
            sid = verify_session_cookie(signed_cookie) if signed_cookie else None
            owner = resolve_session(own_db, sid)
            if owner is None:
                yield _format_sse({"error": "unauthorized"}, event="error")
                return

            past = list_events(own_db, task_id)
            for e in past:
                yield _format_sse(serialize(e))

            q = subscribe(task_id)
            try:
                while True:
                    try:
                        payload = await asyncio.wait_for(q.get(), timeout=HEARTBEAT_INTERVAL)
                        yield _format_sse(payload)
                        if payload.get("event_type") in {"agent_finish", "error"}:
                            # keep stream open briefly after terminal event then close
                            await asyncio.sleep(0.5)
                            break
                    except asyncio.TimeoutError:
                        yield b": heartbeat\n\n"
            finally:
                unsubscribe(task_id, q)
        finally:
            own_db.close()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _format_sse(payload: dict, event: str | None = None) -> bytes:
    parts: list[str] = []
    if event:
        parts.append(f"event: {event}")
    parts.append(f"data: {json.dumps(payload, ensure_ascii=False)}")
    parts.append("")
    parts.append("")
    return "\n".join(parts).encode("utf-8")
