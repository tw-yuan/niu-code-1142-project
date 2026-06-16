import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import SummaryRequest
from app.services.learning_service import LearningService

router = APIRouter(prefix="/summary", tags=["summary"])


@router.post("/stream")
async def stream_summary(
    body: SummaryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LearningService(db)

    async def event_stream():
        full = ""
        try:
            async for chunk in svc.stream_summary(current_user.id, body.doc_id, body.kind, body.count):
                full += chunk
                yield _sse({"type": "chunk", "content": chunk})
            artifact = await svc.save_artifact(current_user.id, body.doc_id, "summary", full)
            yield _sse({"type": "summary_meta", "data": {"summary_id": artifact.id}})
        except Exception as exc:
            yield _sse({"type": "error", "code": "summary_error", "message": str(exc)})
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{doc_id}")
async def get_summary(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    artifact = await LearningService(db).latest_artifact(current_user.id, doc_id, "summary")
    return {"id": artifact.id, "doc_id": artifact.doc_id, "content": artifact.content}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

