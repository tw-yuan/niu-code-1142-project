import json
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, rate_limit
from app.models.tables import User
from app.schemas import ChatSessionCreate, ChatSessionDetail, ChatSessionOut, MessageRequest
from app.services.audit_service import AuditService
from app.services.cost_service import check_quota
from app.services.rag_service import RAGService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/sessions", response_model=ChatSessionOut)
async def create_session(
    body: ChatSessionCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await RAGService(db).create_session(current_user.id, body)
    await AuditService(db).log(
        "chat.session_create",
        user_id=current_user.id,
        resource=f"chat_session:{session['id']}",
        request=request,
        detail={"doc_ids": body.doc_ids, "course_id": body.course_id, "mode": body.mode},
    )
    return session


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RAGService(db).list_sessions(current_user.id)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RAGService(db).get_session_detail(current_user.id, session_id)


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await RAGService(db).delete_session(current_user.id, session_id)
    await AuditService(db).log(
        "chat.session_delete",
        user_id=current_user.id,
        resource=f"chat_session:{session_id}",
        request=request,
    )
    return {"ok": True}


@router.post("/sessions/{session_id}/message", dependencies=[rate_limit("chat_message", 30, 600)])
async def send_message(
    session_id: str,
    body: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rag = RAGService(db)
    await rag.get_session_detail(current_user.id, session_id)
    await check_quota(db, current_user.id)

    async def event_stream():
        full_content = ""
        try:
            async for chunk in rag.stream_answer(session_id, body.content, current_user.id):
                full_content += chunk
                yield _sse({"type": "chunk", "content": chunk})
            citations = await rag.finalize_answer(full_content, await rag.get_last_citations())
            yield _sse({"type": "citations", "data": citations})
            await rag.save_message(
                session_id, current_user.id, body.content, full_content, citations
            )
        except Exception:
            request_id = str(uuid.uuid4())
            yield _sse(
                {
                    "type": "error",
                    "code": "llm_error",
                    "message": f"AI 回應暫時失敗，請稍後再試。錯誤代碼：{request_id}",
                }
            )
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
