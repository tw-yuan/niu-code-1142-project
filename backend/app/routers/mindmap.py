import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import MindmapRequest
from app.services.learning_service import LearningService

router = APIRouter(prefix="/mindmap", tags=["mindmap"])


@router.post("/stream")
async def stream_mindmap(
    body: MindmapRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LearningService(db)

    async def event_stream():
        full = ""
        try:
            async for chunk in svc.stream_mindmap(current_user.id, body.doc_id):
                full += chunk
                yield _sse({"type": "chunk", "content": chunk})
            artifact = await svc.save_artifact(current_user.id, body.doc_id, "mindmap", full)
            yield _sse({"type": "mindmap_meta", "data": {"mindmap_id": artifact.id}})
        except Exception as exc:
            yield _sse({"type": "error", "code": "mindmap_error", "message": str(exc)})
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{doc_id}")
async def get_mindmap(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    artifact = await LearningService(db).latest_artifact(current_user.id, doc_id, "mindmap")
    return {"id": artifact.id, "doc_id": artifact.doc_id, "content": artifact.content}


@router.put("/{artifact_id}")
async def update_mindmap(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _ = current_user
    _ = db
    return {"id": artifact_id, "detail": "Mindmap editing API is reserved for the next phase"}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
