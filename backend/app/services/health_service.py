import asyncio
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_chroma, get_documents_collection, get_redis
from app.services.llm_client import LLMClient
from app.tasks.celery_app import celery_app


async def health_report(db: AsyncSession, include_llm: bool = False) -> dict[str, Any]:
    checks = {
        "database": await _timed(_check_database(db)),
        "redis": await _timed(_check_redis()),
        "chroma": await _timed(_check_chroma()),
        "celery": await _timed(_check_celery()),
    }
    if include_llm:
        checks["llm_api"] = await _timed(_check_llm(db), down_on_error=False)
    statuses = [item["status"] for item in checks.values()]
    if "down" in statuses:
        status = "down"
    elif "degraded" in statuses:
        status = "degraded"
    else:
        status = "ok"
    return {"status": status, "version": "3.0.0", "checks": checks}


async def _timed(coro, down_on_error: bool = True) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        data = await asyncio.wait_for(coro, timeout=3)
        latency = int((time.perf_counter() - started) * 1000)
        return {"status": "ok", "latency_ms": latency, **data}
    except TimeoutError:
        return {"status": "degraded", "latency_ms": 3000, "error": "timeout"}
    except Exception as exc:
        latency = int((time.perf_counter() - started) * 1000)
        return {
            "status": "down" if down_on_error else "degraded",
            "latency_ms": latency,
            "error": exc.__class__.__name__,
        }


async def _check_database(db: AsyncSession) -> dict[str, Any]:
    await db.execute(select(1))
    return {}


async def _check_redis() -> dict[str, Any]:
    await get_redis().ping()
    return {}


async def _check_chroma() -> dict[str, Any]:
    collection = get_documents_collection(get_chroma())
    count = await asyncio.to_thread(collection.count)
    return {"doc_count": count}


async def _check_celery() -> dict[str, Any]:
    def inspect_workers() -> dict[str, Any]:
        inspector = celery_app.control.inspect(timeout=1)
        active = inspector.active() or {}
        reserved = inspector.reserved() or {}
        scheduled = inspector.scheduled() or {}
        if not active and not reserved and not scheduled:
            raise RuntimeError("No Celery workers online")
        return {
            "active_tasks": sum(len(items) for items in active.values()),
            "queued_tasks": sum(len(items) for items in reserved.values())
            + sum(len(items) for items in scheduled.values()),
        }

    return await asyncio.to_thread(inspect_workers)


async def _check_llm(db: AsyncSession) -> dict[str, Any]:
    await LLMClient(db).embed(["x"])
    return {}
