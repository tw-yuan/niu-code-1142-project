import asyncio

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db, get_token_from_request
from app.models.database import SessionLocal, init_db
from app.models.tables import User
from app.routers import admin, auth, chat, documents, flashcards, mindmap, quiz, summary
from app.services.health_service import health_report
from app.services.security import decode_token
from app.services.ws_manager import subscribe_user

app = FastAPI(title="LearnAI API", version="0.1.0")

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
app.include_router(admin.router)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    report = await health_report(db)
    status_code = 503 if report["status"] == "down" else 200
    return JSONResponse(report, status_code=status_code)


@app.get("/health/live")
async def liveness():
    return {"status": "ok", "version": "3.0.0"}


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

    forward_task = asyncio.create_task(subscribe_user(payload["sub"], websocket))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        forward_task.cancel()
    finally:
        forward_task.cancel()
