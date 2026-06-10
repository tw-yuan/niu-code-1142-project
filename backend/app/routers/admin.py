from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import require_admin
from app.models.chat_message import ChatMessage
from app.models.document import Document
from app.models.learning_session import LearningSession
from app.models.user import User
from app.routers.sessions import MessageResponse, message_response
from app.services.document_service import delete_document, process_document
from app.services.rag_service import delete_document_index

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminUserResponse(BaseModel):
    id: int
    nickname: str
    role: str
    document_count: int
    session_count: int
    created_at: datetime


class AdminDocumentResponse(BaseModel):
    id: int
    user_id: int
    owner_nickname: str | None
    original_filename: str
    file_type: str
    file_size: int
    token_count: int
    parse_status: str
    index_status: str
    error_message: str | None
    created_at: datetime


class AdminSessionResponse(BaseModel):
    id: int
    user_id: int
    owner_nickname: str | None
    document_id: int
    document_original_filename: str | None
    direction_key: str
    direction_label: str
    direction_emoji: str | None
    message_count: int
    created_at: datetime


class AdminSessionDetailResponse(AdminSessionResponse):
    messages: list[MessageResponse]


class UpdateUserRoleRequest(BaseModel):
    role: str


@router.get("/overview")
async def overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    users = await db.scalar(select(func.count()).select_from(User))
    documents = await db.scalar(select(func.count()).select_from(Document))
    sessions = await db.scalar(select(func.count()).select_from(LearningSession))
    messages = await db.scalar(select(func.count()).select_from(ChatMessage))
    failed_documents = await db.scalar(
        select(func.count()).select_from(Document).where(Document.parse_status == "failed")
    )
    return {
        "users": users or 0,
        "documents": documents or 0,
        "sessions": sessions or 0,
        "messages": messages or 0,
        "failed_documents": failed_documents or 0,
    }


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    out = []
    for user in users:
        doc_count = await db.scalar(
            select(func.count()).select_from(Document).where(Document.user_id == user.id)
        )
        session_count = await db.scalar(
            select(func.count()).select_from(LearningSession).where(LearningSession.user_id == user.id)
        )
        out.append(
            AdminUserResponse(
                id=user.id,
                nickname=user.nickname,
                role=user.role,
                document_count=doc_count or 0,
                session_count=session_count or 0,
                created_at=user.created_at,
            )
        )
    return out


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user_role(
    user_id: int,
    body: UpdateUserRoleRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    if body.role not in {"student", "admin"}:
        raise HTTPException(status_code=400, detail="role 必須是 student 或 admin")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")
    user.role = body.role
    await db.commit()
    await db.refresh(user)
    doc_count = await db.scalar(select(func.count()).select_from(Document).where(Document.user_id == user.id))
    session_count = await db.scalar(
        select(func.count()).select_from(LearningSession).where(LearningSession.user_id == user.id)
    )
    return AdminUserResponse(
        id=user.id,
        nickname=user.nickname,
        role=user.role,
        document_count=doc_count or 0,
        session_count=session_count or 0,
        created_at=user.created_at,
    )


@router.get("/documents", response_model=list[AdminDocumentResponse])
async def list_documents_admin(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    docs = result.scalars().all()
    out = []
    for doc in docs:
        user = await db.get(User, doc.user_id)
        out.append(
            AdminDocumentResponse(
                id=doc.id,
                user_id=doc.user_id,
                owner_nickname=user.nickname if user else None,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                token_count=doc.token_count,
                parse_status=doc.parse_status,
                index_status=doc.index_status,
                error_message=doc.error_message,
                created_at=doc.created_at,
            )
        )
    return out


@router.delete("/documents/{doc_id}")
async def delete_document_admin(
    doc_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    delete_document_index(doc_id)
    await delete_document(db, doc_id, doc.user_id)
    return {"message": "ok"}


@router.post("/documents/{doc_id}/retry", response_model=AdminDocumentResponse)
async def retry_document_admin(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    doc.parse_status = "uploaded"
    doc.index_status = "pending"
    doc.error_message = None
    doc.directions_cache = None
    await db.commit()
    await db.refresh(doc)
    background_tasks.add_task(process_document, doc.id)
    user = await db.get(User, doc.user_id)
    return AdminDocumentResponse(
        id=doc.id,
        user_id=doc.user_id,
        owner_nickname=user.nickname if user else None,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        token_count=doc.token_count,
        parse_status=doc.parse_status,
        index_status=doc.index_status,
        error_message=doc.error_message,
        created_at=doc.created_at,
    )


@router.get("/sessions", response_model=list[AdminSessionResponse])
async def list_sessions_admin(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    result = await db.execute(select(LearningSession).order_by(LearningSession.created_at.desc()))
    sessions = result.scalars().all()
    out = []
    for session in sessions:
        user = await db.get(User, session.user_id)
        doc = await db.get(Document, session.document_id)
        message_count = await db.scalar(
            select(func.count()).select_from(ChatMessage).where(ChatMessage.session_id == session.id)
        )
        out.append(_session_response(session, user, doc, message_count or 0))
    return out


@router.get("/sessions/{session_id}", response_model=AdminSessionDetailResponse)
async def get_session_admin(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    session = await db.get(LearningSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在")
    user = await db.get(User, session.user_id)
    doc = await db.get(Document, session.document_id)
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    base = _session_response(session, user, doc, len(messages))
    return AdminSessionDetailResponse(**base.model_dump(), messages=[message_response(m) for m in messages])


@router.delete("/sessions/{session_id}")
async def delete_session_admin(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
):
    session = await db.get(LearningSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在")
    await db.delete(session)
    await db.commit()
    return {"message": "ok"}


def _session_response(
    session: LearningSession,
    user: User | None,
    doc: Document | None,
    message_count: int,
) -> AdminSessionResponse:
    return AdminSessionResponse(
        id=session.id,
        user_id=session.user_id,
        owner_nickname=user.nickname if user else None,
        document_id=session.document_id,
        document_original_filename=doc.original_filename if doc else None,
        direction_key=session.direction_key,
        direction_label=session.direction_label,
        direction_emoji=session.direction_emoji,
        message_count=message_count,
        created_at=session.created_at,
    )
