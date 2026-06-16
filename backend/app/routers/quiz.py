import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, rate_limit
from app.models.tables import User
from app.schemas import QuizAttemptRequest, QuizStreamRequest
from app.services.learning_service import LearningService

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/stream", dependencies=[rate_limit("quiz_stream", 5, 3600)])
async def stream_quiz(
    body: QuizStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LearningService(db)

    async def event_stream():
        full = ""
        try:
            async for chunk in svc.stream_quiz(
                current_user.id, body.doc_ids, body.types, body.count, body.difficulty
            ):
                full += chunk
                yield _sse({"type": "chunk", "content": chunk})
            quiz = await svc.save_quiz(
                current_user.id,
                body.doc_ids,
                {"types": body.types, "count": body.count, "difficulty": body.difficulty},
                full,
            )
            yield _sse(
                {"type": "quiz_meta", "data": {"quiz_id": quiz.id, "question_count": body.count}}
            )
        except Exception as exc:
            yield _sse({"type": "error", "code": "quiz_error", "message": str(exc)})
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("")
async def list_quizzes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).list_quizzes(current_user.id)


@router.get("/wrongbook")
async def wrongbook(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).wrongbook(current_user.id)


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).get_quiz(current_user.id, quiz_id)


@router.post("/{quiz_id}/attempt")
async def submit_attempt(
    quiz_id: str,
    body: QuizAttemptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).submit_quiz_attempt(current_user.id, quiz_id, body)


@router.get("/{quiz_id}/attempts")
async def get_attempts(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).quiz_attempts(current_user.id, quiz_id)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
