import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, rate_limit
from app.models.tables import User
from app.schemas import (
    FlashcardCreate,
    FlashcardReviewRequest,
    FlashcardStreamRequest,
    FlashcardUpdate,
    WrongbookFlashcardRequest,
)
from app.services.cost_service import check_quota
from app.services.learning_service import LearningService

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


@router.post("/stream", dependencies=[rate_limit("flashcards_stream", 5, 3600)])
async def stream_flashcards(
    body: FlashcardStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LearningService(db)
    doc_ids = body.doc_ids or ([body.doc_id] if body.doc_id else [])
    if not doc_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No documents selected")
    await check_quota(db, current_user.id)

    async def event_stream():
        full = ""
        try:
            async for chunk in svc.stream_flashcards(
                current_user.id,
                doc_ids,
                body.count,
                course_id=body.course_id,
            ):
                full += chunk
                yield _sse({"type": "chunk", "content": chunk})
            cards = await svc.save_flashcards(current_user.id, doc_ids, full)
            yield _sse({"type": "flashcard_meta", "data": {"count": len(cards)}})
        except Exception as exc:
            yield _sse({"type": "error", "code": "flashcard_error", "message": str(exc)})
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("")
async def list_flashcards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).list_flashcards(current_user.id)


@router.post("")
async def create_flashcard(
    body: FlashcardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).create_flashcard(current_user.id, body)


@router.post("/from-wrongbook")
async def create_from_wrongbook(
    body: WrongbookFlashcardRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).create_flashcards_from_wrongbook(
        current_user.id,
        limit=body.limit,
        quiz_id=body.quiz_id,
    )


@router.put("/{card_id}")
async def update_flashcard(
    card_id: str,
    body: FlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).update_flashcard(current_user.id, card_id, body)


@router.delete("/{card_id}")
async def delete_flashcard(
    card_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await LearningService(db).delete_flashcard(current_user.id, card_id)
    return {"ok": True}


@router.post("/{card_id}/review")
async def review_flashcard(
    card_id: str,
    body: FlashcardReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).review_flashcard(current_user.id, card_id, body.quality)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
