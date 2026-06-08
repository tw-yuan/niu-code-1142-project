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
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: int
    document_id: int
    direction_key: str
    direction_label: str
    direction_emoji: str | None
    created_at: datetime
    document_original_filename: str | None = None

    model_config = {"from_attributes": True}


class SessionDetailResponse(SessionResponse):
    messages: list[MessageResponse] = []


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

    session = LearningSession(
        user_id=user.id,
        document_id=body.document_id,
        direction_key=body.direction_key,
        direction_label=body.direction_label,
        direction_description=body.direction_description,
        direction_emoji=body.direction_emoji,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    r = SessionResponse.model_validate(session)
    r.document_original_filename = doc.original_filename
    return r


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
        doc_result = await db.execute(select(Document).where(Document.id == s.document_id))
        doc = doc_result.scalar_one_or_none()
        r = SessionResponse.model_validate(s)
        r.document_original_filename = doc.original_filename if doc else None
        out.append(r)
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

    r = SessionDetailResponse.model_validate(session)
    r.document_original_filename = doc.original_filename if doc else None
    r.messages = [MessageResponse.model_validate(m) for m in messages]
    return r


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
