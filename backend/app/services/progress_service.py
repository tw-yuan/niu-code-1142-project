from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProgressEvent


@dataclass
class _Listener:
    queue: asyncio.Queue
    loop: asyncio.AbstractEventLoop


_listeners: dict[str, list[_Listener]] = defaultdict(list)


def write_event(
    db: Session,
    task_id: str,
    event_type: str,
    message: str,
    detail: dict | list | None = None,
) -> ProgressEvent:
    event = ProgressEvent(
        task_id=task_id,
        event_type=event_type,
        message=message,
        detail=detail,
    )
    db.add(event)
    db.flush()
    _broadcast(task_id, _serialize(event))
    return event


def list_events(db: Session, task_id: str) -> list[ProgressEvent]:
    stmt = (
        select(ProgressEvent)
        .where(ProgressEvent.task_id == task_id)
        .order_by(ProgressEvent.created_at.asc(), ProgressEvent.id.asc())
    )
    return list(db.execute(stmt).scalars().all())


def subscribe(task_id: str) -> asyncio.Queue:
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _listeners[task_id].append(_Listener(queue=q, loop=loop))
    return q


def unsubscribe(task_id: str, q: asyncio.Queue) -> None:
    lst = _listeners.get(task_id)
    if not lst:
        return
    lst[:] = [li for li in lst if li.queue is not q]
    if not lst:
        _listeners.pop(task_id, None)


def _broadcast(task_id: str, payload: dict[str, Any]) -> None:
    for listener in list(_listeners.get(task_id, [])):
        try:
            listener.loop.call_soon_threadsafe(_safe_put, listener.queue, payload)
        except RuntimeError:
            # Event loop closed — drop the listener
            try:
                _listeners.get(task_id, []).remove(listener)
            except ValueError:
                pass


def _safe_put(queue: asyncio.Queue, payload: dict[str, Any]) -> None:
    try:
        queue.put_nowait(payload)
    except asyncio.QueueFull:
        pass


def _serialize(event: ProgressEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "task_id": event.task_id,
        "event_type": event.event_type,
        "message": event.message,
        "detail": event.detail,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def serialize(event: ProgressEvent) -> dict[str, Any]:
    return _serialize(event)
