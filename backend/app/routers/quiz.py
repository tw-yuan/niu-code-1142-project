import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, rate_limit
from app.models.tables import User
from app.schemas import CourseQuizPublishRequest, QuizAttemptRequest, QuizStreamRequest
from app.services.cost_service import check_quota
from app.services.generation_service import GenerationService
from app.services.learning_service import LearningService
from app.tasks.generation_tasks import run_generation_task

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/jobs", dependencies=[rate_limit("quiz_job", 5, 3600)])
async def create_quiz_job(
    body: QuizStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await check_quota(db, current_user.id)
    task = await GenerationService(db).create_task(
        current_user.id,
        "quiz",
        body.model_dump(),
    )
    run_generation_task.delay(task["id"])
    return task


@router.post("/stream", dependencies=[rate_limit("quiz_stream", 5, 3600)])
async def stream_quiz(
    body: QuizStreamRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LearningService(db)
    await check_quota(db, current_user.id)

    async def event_stream():
        full = ""
        try:
            async for chunk in svc.stream_quiz(
                current_user.id,
                body.doc_ids,
                body.types,
                body.count,
                body.difficulty,
                course_id=body.course_id if body.publish_to_course else None,
            ):
                full += chunk
                yield _sse({"type": "chunk", "content": chunk})
            quiz = await svc.save_quiz(
                current_user.id,
                body.doc_ids,
                {
                    "types": body.types,
                    "count": body.count,
                    "difficulty": body.difficulty,
                    "course_id": body.course_id,
                    "published": body.publish_to_course,
                },
                full,
                title=body.title,
                course_id=body.course_id,
                publish_to_course=body.publish_to_course,
                due_at=body.due_at,
                available_from=body.available_from,
                answer_visible_at=body.answer_visible_at,
                attempt_limit=body.attempt_limit,
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


@router.post("/{quiz_id}/publish/{course_id}")
async def publish_quiz(
    quiz_id: str,
    course_id: str,
    body: CourseQuizPublishRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).publish_quiz_to_course(
        current_user.id,
        course_id,
        quiz_id,
        title=body.title,
        due_at=body.due_at,
        available_from=body.available_from,
        answer_visible_at=body.answer_visible_at,
        attempt_limit=body.attempt_limit,
        status_value=body.status,
    )


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LearningService(db).get_quiz(current_user.id, quiz_id)


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await LearningService(db).delete_quiz(current_user.id, quiz_id)
    return {"ok": True}


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
