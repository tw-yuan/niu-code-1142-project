import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.progress_event import ProgressEvent

_task_queues: dict[str, asyncio.Queue] = {}


def get_task_queue(task_id: str) -> asyncio.Queue:
    if task_id not in _task_queues:
        _task_queues[task_id] = asyncio.Queue()
    return _task_queues[task_id]


def cleanup_task_queue(task_id: str):
    _task_queues.pop(task_id, None)


async def add_progress_event(
    task_id: str,
    event_type: str,
    message: str,
    detail: dict | None = None,
):
    async with async_session() as db:
        event = ProgressEvent(
            task_id=task_id,
            event_type=event_type,
            message=message,
            detail=detail,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()

    queue = get_task_queue(task_id)
    await queue.put({
        "event_type": event_type,
        "message": message,
        "detail": detail,
    })


async def get_events_for_task(db: AsyncSession, task_id: str) -> list[ProgressEvent]:
    result = await db.execute(
        select(ProgressEvent)
        .where(ProgressEvent.task_id == task_id)
        .order_by(ProgressEvent.created_at)
    )
    return list(result.scalars().all())
