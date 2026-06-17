import asyncio
import contextlib
import time
import uuid

from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_redis, get_token_from_request, require_admin
from app.models.database import SessionLocal, init_db
from app.models.tables import User
from app.routers import (
    admin,
    auth,
    chat,
    courses,
    documents,
    flashcards,
    generation,
    goals,
    legal,
    mindmap,
    notes,
    quiz,
    summary,
)
from app.services.health_service import health_report
from app.services.security import decode_token
from app.services.ws_manager import subscribe_user

app = FastAPI(
    title="LearnAI API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(summary.router)
app.include_router(quiz.router)
app.include_router(mindmap.router)
app.include_router(flashcards.router)
app.include_router(generation.router)
app.include_router(notes.router)
app.include_router(goals.router)
app.include_router(courses.router)
app.include_router(legal.router)
app.include_router(admin.router)


@app.middleware("http")
async def global_rate_limit(request: Request, call_next):
    limit = 120
    window_seconds = 60
    now = time.time()
    retry_after = window_seconds
    try:
        key = f"rl:global:{_client_ip(request)}"
        client = get_redis()
        await client.zremrangebyscore(key, 0, now - window_seconds)
        count = await client.zcard(key)
        if count >= limit:
            oldest = await client.zrange(key, 0, 0, withscores=True)
            retry_after = (
                max(1, int(oldest[0][1] + window_seconds - now)) if oldest else window_seconds
            )
            return JSONResponse(
                {
                    "detail": {
                        "code": "rate_limited",
                        "message": "請求過於頻繁，請稍後再試",
                    }
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                },
            )
        await client.zadd(key, {f"{now}:{uuid.uuid4()}": now})
        await client.expire(key, window_seconds)
    except Exception:
        return await call_next(request)

    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count - 1))
    response.headers["X-RateLimit-Reset"] = str(int(now + window_seconds))
    return response


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    report = await health_report(db)
    status_code = 503 if report["status"] == "down" else 200
    return JSONResponse(report, status_code=status_code)


@app.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    report = await health_report(db)
    status_code = 503 if report["status"] == "down" else 200
    return JSONResponse(report, status_code=status_code)


@app.get("/health/live")
async def liveness():
    return {"status": "ok", "version": "3.0.0"}


@app.get("/health/deep")
async def deep_health(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    report = await health_report(db, include_llm=True)
    status_code = 503 if report["status"] == "down" else 200
    return JSONResponse(report, status_code=status_code)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = get_token_from_request(websocket)
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = decode_token(token, "access")
    except Exception:
        await websocket.close(code=1008)
        return
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.id == payload["sub"]))
        ).scalar_one_or_none()
        if user is None or not user.is_active:
            await websocket.close(code=1008)
            return

    await websocket.accept()
    forward_task = asyncio.create_task(subscribe_user(payload["sub"], websocket))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await forward_task


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
