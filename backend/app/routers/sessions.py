import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Annotated
from datetime import datetime

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.learning_session import LearningSession
from app.models.chat_message import ChatMessage
from app.services.chat_service import stream_chat_response

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(BaseModel):
    document_id: int
    direction_key: str
    direction_label: str
    direction_description: str | None = None
    direction_emoji: str | None = None


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    context_chunks_used: list[dict] | None = None
    quiz_metadata: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: int
    document_id: int
    direction_key: str
    direction_label: str
    direction_emoji: str | None
    title: str | None = None
    message_count: int = 0
    last_message_preview: str | None = None
    quiz_attempts: int = 0
    quiz_average_score: float | None = None
    created_at: datetime
    document_original_filename: str | None = None

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse] = []


class UpdateSessionRequest(BaseModel):
    title: str | None = None


def message_response(message: ChatMessage) -> MessageResponse:
    sources = None
    quiz_metadata = None
    if message.context_chunks_used:
        try:
            sources = json.loads(message.context_chunks_used)
        except json.JSONDecodeError:
            sources = None
    if message.quiz_metadata:
        try:
            quiz_metadata = json.loads(message.quiz_metadata)
        except json.JSONDecodeError:
            quiz_metadata = None
    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        context_chunks_used=sources,
        quiz_metadata=quiz_metadata,
        created_at=message.created_at,
    )


def _quiz_summary(messages: list[ChatMessage]) -> tuple[int, float | None]:
    scores = []
    attempts = 0
    for message in messages:
        if not message.quiz_metadata:
            continue
        try:
            metadata = json.loads(message.quiz_metadata)
        except json.JSONDecodeError:
            continue
        if metadata.get("kind") == "quiz":
            attempts += 1
            if isinstance(metadata.get("score"), (int, float)):
                scores.append(float(metadata["score"]))
    return attempts, round(sum(scores) / len(scores), 1) if scores else None


async def _session_response(db: AsyncSession, session: LearningSession, doc: Document | None = None) -> SessionResponse:
    if doc is None:
        doc_result = await db.execute(select(Document).where(Document.id == session.document_id))
        doc = doc_result.scalar_one_or_none()
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    )
    messages = list(msg_result.scalars().all())
    attempts, average_score = _quiz_summary(messages)
    last_message = messages[-1].content if messages else None
    r = SessionResponse.model_validate(session)
    r.document_original_filename = doc.original_filename if doc else None
    r.message_count = len(messages)
    r.last_message_preview = last_message[:140] if last_message else None
    r.quiz_attempts = attempts
    r.quiz_average_score = average_score
    return r


@router.post("", response_model=SessionResponse)
async def create_session(
    body: CreateSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    doc_result = await db.execute(
        select(Document).where(Document.id == body.document_id, Document.user_id == user.id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    if doc.parse_status != "ready":
        raise HTTPException(status_code=400, detail="文件尚未解析完成")

    session = LearningSession(
        user_id=user.id,
        document_id=body.document_id,
        direction_key=body.direction_key,
        direction_label=body.direction_label,
        direction_description=body.direction_description,
        direction_emoji=body.direction_emoji,
        title=f"{body.direction_label} - {doc.original_filename}",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return await _session_response(db, session, doc)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(LearningSession)
        .where(LearningSession.user_id == user.id)
        .order_by(LearningSession.created_at.desc())
    )
    sessions = result.scalars().all()
    out = []
    for s in sessions:
        out.append(await _session_response(db, s))
    return out


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(LearningSession).where(
            LearningSession.id == session_id, LearningSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在")

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = msg_result.scalars().all()

    doc_result = await db.execute(select(Document).where(Document.id == session.document_id))
    doc = doc_result.scalar_one_or_none()

    attempts, average_score = _quiz_summary(list(messages))
    last_message = messages[-1].content if messages else None
    return SessionDetailResponse(
        id=session.id,
        document_id=session.document_id,
        direction_key=session.direction_key,
        direction_label=session.direction_label,
        direction_emoji=session.direction_emoji,
        title=session.title,
        message_count=len(messages),
        last_message_preview=last_message[:140] if last_message else None,
        quiz_attempts=attempts,
        quiz_average_score=average_score,
        created_at=session.created_at,
        document_original_filename=doc.original_filename if doc else None,
        messages=[message_response(m) for m in messages],
    )


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: int,
    body: UpdateSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(LearningSession).where(
            LearningSession.id == session_id, LearningSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在")
    title = (body.title or "").strip()
    session.title = title[:160] if title else None
    await db.commit()
    await db.refresh(session)
    return await _session_response(db, session)


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(LearningSession).where(
            LearningSession.id == session_id, LearningSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在")
    await db.delete(session)
    await db.commit()
    return {"message": "ok"}


@router.post("/{session_id}/messages")
async def send_message(
    session_id: int,
    body: MessageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    result = await db.execute(
        select(LearningSession).where(
            LearningSession.id == session_id, LearningSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在")
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="訊息不得為空")

    return StreamingResponse(
        stream_chat_response(db, session, body.content.strip()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
