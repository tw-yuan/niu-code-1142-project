from __future__ import annotations

import json
import secrets
import string
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import (
    ChatMessage,
    ChatSession,
    Course,
    CourseDocument,
    CourseMember,
    CourseQuiz,
    Document,
    Flashcard,
    Note,
    Quiz,
    QuizAttempt,
    User,
    now_iso,
)
from app.schemas import (
    CourseCreate,
    CourseDocumentRequest,
    CourseJoinRequest,
    CourseMemberRoleUpdate,
    CourseUpdate,
)


class CoursesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, body: CourseCreate) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None or user.role not in {"teacher", "admin"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher role required to create courses",
            )
        course = Course(
            owner_id=user_id,
            title=body.title,
            description=body.description,
            join_code=await self._new_join_code(),
        )
        self.db.add(course)
        await self.db.flush()
        self.db.add(CourseMember(course_id=course.id, user_id=user_id, role="instructor"))
        await self.db.commit()
        await self.db.refresh(course)
        return await self._out_for_member(course, user_id)

    async def list(self, user_id: str) -> list[dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(Course)
                .join(CourseMember, CourseMember.course_id == Course.id)
                .where(and_(CourseMember.user_id == user_id, Course.is_active == 1))
                .order_by(desc(Course.created_at))
            )
        ).scalars().all()
        return [await self._out_for_member(row, user_id) for row in rows]

    async def get(self, user_id: str, course_id: str) -> dict[str, Any]:
        course = await self._get_course(course_id)
        await self.require_member(user_id, course_id)
        return await self._out_for_member(course, user_id, include_detail=True)

    async def update(self, user_id: str, course_id: str, body: CourseUpdate) -> dict[str, Any]:
        course = await self._get_course(course_id)
        await self.require_role(user_id, course_id, {"instructor"})
        if "title" in body.model_fields_set and body.title is not None:
            course.title = body.title
        if "description" in body.model_fields_set:
            course.description = body.description
        await self.db.commit()
        await self.db.refresh(course)
        return await self._out_for_member(course, user_id, include_detail=True)

    async def reset_join_code(self, user_id: str, course_id: str) -> dict[str, Any]:
        course = await self._get_course(course_id)
        if course.owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course owner only")
        course.join_code = await self._new_join_code()
        await self.db.commit()
        await self.db.refresh(course)
        return await self._out_for_member(course, user_id, include_detail=True)

    async def delete(self, user_id: str, course_id: str) -> None:
        course = await self._get_course(course_id)
        if course.owner_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course owner only")
        await self.db.delete(course)
        await self.db.commit()

    async def join(self, user_id: str, body: CourseJoinRequest) -> dict[str, Any]:
        course = (
            await self.db.execute(
                select(Course).where(
                    and_(Course.join_code == body.join_code.upper(), Course.is_active == 1)
                )
            )
        ).scalar_one_or_none()
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        member = (
            await self.db.execute(
                select(CourseMember).where(
                    and_(CourseMember.course_id == course.id, CourseMember.user_id == user_id)
                )
            )
        ).scalar_one_or_none()
        if member is None:
            self.db.add(CourseMember(course_id=course.id, user_id=user_id, role="student"))
            await self.db.commit()
        return await self._out_for_member(course, user_id)

    async def add_document(
        self, user_id: str, course_id: str, body: CourseDocumentRequest
    ) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        doc = (
            await self.db.execute(
                select(Document).where(
                    and_(
                        Document.id == body.doc_id,
                        Document.user_id == user_id,
                        Document.status == "ready",
                    )
                )
            )
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        existing = (
            await self.db.execute(
                select(CourseDocument).where(
                    and_(CourseDocument.course_id == course_id, CourseDocument.doc_id == body.doc_id)
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            self.db.add(CourseDocument(course_id=course_id, doc_id=body.doc_id))
            await self.db.commit()
        return {"ok": True}

    async def remove_document(self, user_id: str, course_id: str, doc_id: str) -> None:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        item = (
            await self.db.execute(
                select(CourseDocument).where(
                    and_(CourseDocument.course_id == course_id, CourseDocument.doc_id == doc_id)
                )
            )
        ).scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course document not found")
        await self.db.delete(item)
        await self.db.commit()

    async def update_member_role(
        self,
        user_id: str,
        course_id: str,
        member_user_id: str,
        body: CourseMemberRoleUpdate,
    ) -> dict[str, Any]:
        course = await self._get_course(course_id)
        actor = await self.require_role(user_id, course_id, {"instructor"})
        member = await self._get_member(course_id, member_user_id)
        if member_user_id == course.owner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course owner role is fixed")
        if course.owner_id != user_id and (actor.role != "instructor" or member.role == "instructor"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course owner only")
        if course.owner_id != user_id and body.role == "instructor":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course owner only")
        member.role = body.role
        await self.db.commit()
        return {"ok": True}

    async def remove_member(self, user_id: str, course_id: str, member_user_id: str) -> None:
        course = await self._get_course(course_id)
        actor = await self.require_role(user_id, course_id, {"instructor", "ta"})
        member = await self._get_member(course_id, member_user_id)
        if member_user_id == course.owner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course owner cannot be removed")
        if actor.role == "ta":
            if member.role != "student":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Instructor only")
        elif course.owner_id != user_id and member.role == "instructor":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course owner only")
        await self.db.delete(member)
        await self.db.commit()

    async def leave(self, user_id: str, course_id: str) -> None:
        course = await self._get_course(course_id)
        if course.owner_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Course owner cannot leave the course",
            )
        member = await self._get_member(course_id, user_id)
        await self.db.delete(member)
        await self.db.commit()

    async def members(self, user_id: str, course_id: str) -> list[dict[str, Any]]:
        course = await self._get_course(course_id)
        requester = await self.require_member(user_id, course_id)
        can_view_email = course.owner_id == user_id or requester.role in {"instructor", "ta"}
        rows = (
            await self.db.execute(
                select(CourseMember, User.username, User.email)
                .join(User, User.id == CourseMember.user_id)
                .where(CourseMember.course_id == course_id)
                .order_by(CourseMember.joined_at)
            )
        ).all()
        return [
            {
                "user_id": member.user_id,
                "username": username,
                "email": email if can_view_email or member.user_id == user_id else None,
                "role": member.role,
                "joined_at": member.joined_at,
            }
            for member, username, email in rows
        ]

    async def progress(self, user_id: str, course_id: str) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        doc_ids = await self.course_document_ids(user_id, course_id)
        members = await self.members(user_id, course_id)
        course_quiz_rows = (
            await self.db.execute(
                select(CourseQuiz, Quiz)
                .join(Quiz, Quiz.id == CourseQuiz.quiz_id)
                .where(and_(CourseQuiz.course_id == course_id, CourseQuiz.status == "published"))
                .order_by(desc(CourseQuiz.published_at))
            )
        ).all()
        course_quiz_ids = [quiz.id for _, quiz in course_quiz_rows]
        rows = []
        for member in members:
            member_id = member["user_id"]
            chat_sessions = (
                await self.db.execute(
                    select(ChatSession)
                    .where(and_(ChatSession.user_id == member_id, ChatSession.course_id == course_id))
                    .order_by(desc(ChatSession.updated_at))
                )
            ).scalars().all()
            chat_session_ids = [session.id for session in chat_sessions]
            message_count = 0
            if chat_session_ids:
                message_count = (
                    await self.db.execute(
                        select(func.count(ChatMessage.id)).where(ChatMessage.session_id.in_(chat_session_ids))
                    )
                ).scalar_one()
            note_count = 0
            if chat_session_ids:
                note_count = (
                    await self.db.execute(
                        select(func.count(Note.id)).where(
                            and_(Note.user_id == member_id, Note.session_id.in_(chat_session_ids))
                        )
                    )
                ).scalar_one()
            flashcards = []
            if doc_ids:
                flashcards = (
                    await self.db.execute(
                        select(Flashcard).where(
                            and_(Flashcard.user_id == member_id, Flashcard.doc_id.in_(doc_ids))
                        )
                    )
                ).scalars().all()
            attempts = []
            if course_quiz_ids:
                attempts = (
                    await self.db.execute(
                        select(QuizAttempt)
                        .where(
                            and_(
                                QuizAttempt.user_id == member_id,
                                QuizAttempt.quiz_id.in_(course_quiz_ids),
                            )
                        )
                        .order_by(desc(QuizAttempt.completed_at))
                    )
                ).scalars().all()
            attempted_quiz_ids = {attempt.quiz_id for attempt in attempts}
            avg_score = (
                sum(float(attempt.total_score or 0) for attempt in attempts) / len(attempts)
                if attempts
                else 0.0
            )
            last_activity = max(
                [
                    value
                    for value in [
                        chat_sessions[0].updated_at if chat_sessions else None,
                        attempts[0].completed_at if attempts else None,
                    ]
                    if value
                ],
                default=None,
            )
            due_flashcards = sum(1 for card in flashcards if card.next_review <= now_iso())
            mastered_flashcards = sum(1 for card in flashcards if card.repetition >= 2)
            rows.append(
                {
                    **member,
                    "chat_sessions": len(chat_sessions),
                    "chat_messages": int(message_count),
                    "notes": int(note_count),
                    "flashcards": len(flashcards),
                    "flashcards_due": due_flashcards,
                    "flashcards_mastered": mastered_flashcards,
                    "quizzes": len(attempted_quiz_ids),
                    "assigned_quizzes": len(course_quiz_ids),
                    "quiz_attempts": len(attempts),
                    "quiz_avg_score": round(avg_score, 4),
                    "last_activity_at": last_activity,
                    "risk_level": _risk_level(
                        assigned_quizzes=len(course_quiz_ids),
                        completed_quizzes=len(attempted_quiz_ids),
                        avg_score=avg_score,
                        chat_messages=int(message_count),
                        last_activity_at=last_activity,
                    ),
                }
            )
        return {
            "course_id": course_id,
            "document_count": len(doc_ids),
            "published_quizzes": len(course_quiz_ids),
            "students": rows,
            "quiz_summary": await self._course_quiz_summary(course_id, course_quiz_rows, members),
        }

    async def course_document_ids(self, user_id: str, course_id: str) -> list[str]:
        await self._get_course(course_id)
        await self.require_member(user_id, course_id)
        rows = (
            await self.db.execute(
                select(CourseDocument.doc_id)
                .join(Document, Document.id == CourseDocument.doc_id)
                .where(and_(CourseDocument.course_id == course_id, Document.status == "ready"))
            )
        ).scalars().all()
        return list(rows)

    async def require_member(self, user_id: str, course_id: str) -> CourseMember:
        await self._get_course(course_id)
        member = (
            await self.db.execute(
                select(CourseMember).where(
                    and_(CourseMember.course_id == course_id, CourseMember.user_id == user_id)
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course member only")
        return member

    async def require_role(
        self, user_id: str, course_id: str, roles: set[str]
    ) -> CourseMember:
        course = await self._get_course(course_id)
        member = await self.require_member(user_id, course_id)
        if course.owner_id == user_id:
            return member
        if member.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient course role")
        return member

    async def _get_course(self, course_id: str) -> Course:
        course = (
            await self.db.execute(select(Course).where(Course.id == course_id))
        ).scalar_one_or_none()
        if course is None or not course.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return course

    async def _get_member(self, course_id: str, user_id: str) -> CourseMember:
        member = (
            await self.db.execute(
                select(CourseMember).where(
                    and_(CourseMember.course_id == course_id, CourseMember.user_id == user_id)
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course member not found")
        return member

    async def _out_for_member(
        self,
        course: Course,
        user_id: str,
        include_detail: bool = False,
    ) -> dict[str, Any]:
        member = await self.require_member(user_id, course.id)
        data = {
            "id": course.id,
            "owner_id": course.owner_id,
            "title": course.title,
            "description": course.description,
            "join_code": course.join_code if course.owner_id == user_id or member.role in {"instructor", "ta"} else None,
            "role": member.role,
            "is_active": course.is_active,
            "created_at": course.created_at,
        }
        if include_detail:
            docs = (
                await self.db.execute(
                    select(Document)
                    .join(CourseDocument, CourseDocument.doc_id == Document.id)
                    .where(CourseDocument.course_id == course.id)
                    .order_by(desc(CourseDocument.added_at))
                )
            ).scalars().all()
            data["documents"] = [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.status,
                    "page_count": doc.page_count,
                    "chunk_count": doc.chunk_count,
                    "created_at": doc.created_at,
                }
                for doc in docs
            ]
        return data

    async def _new_join_code(self) -> str:
        alphabet = string.ascii_uppercase + string.digits
        for _ in range(20):
            code = "".join(secrets.choice(alphabet) for _ in range(6))
            exists = (
                await self.db.execute(select(Course.id).where(Course.join_code == code))
            ).scalar_one_or_none()
            if exists is None:
                return code
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create join code")

    async def _course_quiz_summary(
        self,
        course_id: str,
        course_quiz_rows: list[tuple[CourseQuiz, Quiz]],
        members: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        student_ids = [member["user_id"] for member in members if member["role"] == "student"]
        summaries: list[dict[str, Any]] = []
        for course_quiz, quiz in course_quiz_rows:
            attempts = (
                await self.db.execute(
                    select(QuizAttempt).where(
                        and_(QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id.in_(student_ids))
                    )
                )
            ).scalars().all() if student_ids else []
            questions = _safe_json_list(quiz.questions)
            item_stats = _item_analysis(questions, attempts)
            score_avg = (
                sum(float(attempt.total_score or 0) for attempt in attempts) / len(attempts)
                if attempts
                else 0.0
            )
            summaries.append(
                {
                    "course_quiz_id": course_quiz.id,
                    "quiz_id": quiz.id,
                    "course_id": course_id,
                    "title": course_quiz.title,
                    "due_at": course_quiz.due_at,
                    "published_at": course_quiz.published_at,
                    "student_count": len(student_ids),
                    "submission_count": len({attempt.user_id for attempt in attempts}),
                    "attempt_count": len(attempts),
                    "score_avg": round(score_avg, 4),
                    "weak_items": [item for item in item_stats if item["correct_rate"] < 0.6],
                    "items": item_stats,
                }
            )
        return summaries


def _safe_json_list(value: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _answer_for(answers: dict[str, Any] | list[Any], index: int) -> Any:
    if isinstance(answers, dict):
        return answers.get(str(index), answers.get(index))
    return answers[index] if index < len(answers) else None


def _answers_match(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return str(actual).strip() == str(expected).strip()


def _item_analysis(questions: list[dict[str, Any]], attempts: list[QuizAttempt]) -> list[dict[str, Any]]:
    stats: list[dict[str, Any]] = []
    parsed_attempts = []
    for attempt in attempts:
        try:
            parsed_attempts.append(json.loads(attempt.answers))
        except json.JSONDecodeError:
            parsed_attempts.append({})
    for index, question in enumerate(questions):
        distribution: dict[str, int] = {}
        correct = 0
        answered = 0
        for answers in parsed_attempts:
            actual = _answer_for(answers, index)
            if actual is None:
                continue
            answered += 1
            key = str(actual).strip()
            distribution[key] = distribution.get(key, 0) + 1
            if _answers_match(actual, question.get("answer")):
                correct += 1
        stats.append(
            {
                "question_index": index,
                "question": question.get("question") or question.get("prompt"),
                "answer": question.get("answer"),
                "source_page": question.get("source_page"),
                "answered": answered,
                "correct": correct,
                "correct_rate": round(correct / answered, 4) if answered else 0.0,
                "distribution": distribution,
                "explanation": question.get("explanation"),
            }
        )
    return stats


def _risk_level(
    assigned_quizzes: int,
    completed_quizzes: int,
    avg_score: float,
    chat_messages: int,
    last_activity_at: str | None,
) -> str:
    if assigned_quizzes and completed_quizzes == 0:
        return "high"
    if avg_score and avg_score < 0.6:
        return "high"
    if assigned_quizzes and completed_quizzes < assigned_quizzes:
        return "medium"
    if chat_messages == 0 and not last_activity_at:
        return "medium"
    return "ok"
