from __future__ import annotations

import contextlib
import csv
import io
import json
import secrets
import string
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import (
    ChatMessage,
    ChatSession,
    Course,
    CourseAnnouncement,
    CourseAnnouncementRead,
    CourseAssignment,
    CourseAssignmentSubmission,
    CourseDocument,
    CourseHelpRequest,
    CourseHelpRequestEvent,
    CourseMember,
    CourseQuestionBankItem,
    CourseQuiz,
    Document,
    Flashcard,
    LearningArtifact,
    Note,
    Quiz,
    QuizAttempt,
    User,
    now_iso,
)
from app.schemas import (
    CourseAnnouncementCreate,
    CourseAnnouncementUpdate,
    CourseAssignmentCreate,
    CourseAssignmentSubmit,
    CourseAssignmentUpdate,
    CourseCreate,
    CourseDocumentRequest,
    CourseHelpRequestCreate,
    CourseHelpRequestUpdate,
    CourseJoinRequest,
    CourseMemberBatchUpdate,
    CourseMemberRoleUpdate,
    CourseQuestionReviewBatchUpdate,
    CourseQuestionReviewUpdate,
    CourseUpdate,
)
from app.services.ws_manager import push_to_user


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
            (
                await self.db.execute(
                    select(Course)
                    .join(CourseMember, CourseMember.course_id == Course.id)
                    .where(and_(CourseMember.user_id == user_id, Course.is_active == 1))
                    .order_by(desc(Course.created_at))
                )
            )
            .scalars()
            .all()
        )
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
        return await self.add_documents(user_id, course_id, body)

    async def add_documents(
        self, user_id: str, course_id: str, body: CourseDocumentRequest
    ) -> dict[str, Any]:
        doc_ids = _course_document_ids(body)
        if not doc_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No documents selected",
            )
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        docs = (
            (
                await self.db.execute(
                    select(Document.id).where(
                        and_(
                            Document.id.in_(doc_ids),
                            Document.user_id == user_id,
                            Document.status == "ready",
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        if set(docs) != set(doc_ids):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        existing_rows = (
            (
                await self.db.execute(
                    select(CourseDocument).where(
                        and_(
                            CourseDocument.course_id == course_id,
                            CourseDocument.doc_id.in_(doc_ids),
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        existing_by_doc_id = {item.doc_id: item for item in existing_rows}
        added = 0
        reactivated = 0
        skipped = 0
        for doc_id in doc_ids:
            existing = existing_by_doc_id.get(doc_id)
            if existing is None:
                self.db.add(
                    CourseDocument(
                        course_id=course_id,
                        doc_id=doc_id,
                        added_by=user_id,
                        version_label=body.version_label,
                        note=body.note,
                    )
                )
                added += 1
            elif not existing.is_active:
                existing.is_active = 1
                existing.removed_at = None
                existing.removed_by = None
                existing.added_by = user_id
                existing.version_label = body.version_label
                existing.note = body.note
                reactivated += 1
            else:
                if body.version_label is not None:
                    existing.version_label = body.version_label
                if body.note is not None:
                    existing.note = body.note
                skipped += 1
        if added or reactivated or skipped:
            await self.db.commit()
        return {
            "ok": True,
            "doc_ids": doc_ids,
            "added": added,
            "reactivated": reactivated,
            "skipped": skipped,
        }

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course document not found"
            )
        item.is_active = 0
        item.removed_at = now_iso()
        item.removed_by = user_id
        await self.db.commit()

    async def remove_documents(
        self, user_id: str, course_id: str, doc_ids: list[str]
    ) -> dict[str, Any]:
        if not doc_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No documents selected",
            )
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        rows = (
            (
                await self.db.execute(
                    select(CourseDocument).where(
                        and_(
                            CourseDocument.course_id == course_id,
                            CourseDocument.doc_id.in_(doc_ids),
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        by_doc_id = {row.doc_id: row for row in rows}
        missing = [doc_id for doc_id in doc_ids if doc_id not in by_doc_id]
        now = now_iso()
        removed = 0
        skipped = 0
        for doc_id in doc_ids:
            item = by_doc_id.get(doc_id)
            if item is None:
                continue
            if item.is_active:
                item.is_active = 0
                item.removed_at = now
                item.removed_by = user_id
                removed += 1
            else:
                skipped += 1
        await self.db.commit()
        return {
            "ok": True,
            "doc_ids": doc_ids,
            "removed": removed,
            "skipped": skipped,
            "missing": missing,
        }

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Course owner role is fixed"
            )
        if course.owner_id != user_id and (
            actor.role != "instructor" or member.role == "instructor"
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course owner only")
        if course.owner_id != user_id and body.role == "instructor":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course owner only")
        member.role = body.role
        await self.db.commit()
        return {"ok": True}

    async def batch_members(
        self,
        user_id: str,
        course_id: str,
        body: CourseMemberBatchUpdate,
    ) -> dict[str, Any]:
        if body.action == "remove":
            removed = 0
            skipped: list[str] = []
            for member_user_id in body.user_ids:
                try:
                    await self.remove_member(user_id, course_id, member_user_id)
                    removed += 1
                except HTTPException as exc:
                    if exc.status_code in {
                        status.HTTP_400_BAD_REQUEST,
                        status.HTTP_403_FORBIDDEN,
                        status.HTTP_404_NOT_FOUND,
                    }:
                        skipped.append(member_user_id)
                    else:
                        raise
            return {"ok": True, "action": "remove", "removed": removed, "skipped": skipped}

        if body.role is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role is required")
        updated = 0
        skipped = []
        for member_user_id in body.user_ids:
            try:
                await self.update_member_role(
                    user_id,
                    course_id,
                    member_user_id,
                    CourseMemberRoleUpdate(role=body.role),
                )
                updated += 1
            except HTTPException as exc:
                if exc.status_code in {
                    status.HTTP_400_BAD_REQUEST,
                    status.HTTP_403_FORBIDDEN,
                    status.HTTP_404_NOT_FOUND,
                }:
                    skipped.append(member_user_id)
                else:
                    raise
        return {"ok": True, "action": "update_role", "updated": updated, "skipped": skipped}

    async def remove_member(self, user_id: str, course_id: str, member_user_id: str) -> None:
        course = await self._get_course(course_id)
        actor = await self.require_role(user_id, course_id, {"instructor", "ta"})
        member = await self._get_member(course_id, member_user_id)
        if member_user_id == course.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Course owner cannot be removed"
            )
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
                (
                    await self.db.execute(
                        select(ChatSession)
                        .where(
                            and_(
                                ChatSession.user_id == member_id, ChatSession.course_id == course_id
                            )
                        )
                        .order_by(desc(ChatSession.updated_at))
                    )
                )
                .scalars()
                .all()
            )
            chat_session_ids = [session.id for session in chat_sessions]
            message_count = 0
            if chat_session_ids:
                message_count = (
                    await self.db.execute(
                        select(func.count(ChatMessage.id)).where(
                            ChatMessage.session_id.in_(chat_session_ids)
                        )
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
                    (
                        await self.db.execute(
                            select(Flashcard).where(
                                and_(Flashcard.user_id == member_id, Flashcard.doc_id.in_(doc_ids))
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
            attempts = []
            if course_quiz_ids:
                attempts = (
                    (
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
                    )
                    .scalars()
                    .all()
                )
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

    async def progress_csv(self, user_id: str, course_id: str) -> str:
        data = await self.progress(user_id, course_id)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "username",
                "email",
                "role",
                "chat_sessions",
                "chat_messages",
                "notes",
                "flashcards",
                "flashcards_due",
                "flashcards_mastered",
                "completed_quizzes",
                "assigned_quizzes",
                "quiz_attempts",
                "quiz_avg_percent",
                "last_activity_at",
                "risk_level",
            ]
        )
        for item in data["students"]:
            writer.writerow(
                [
                    item["username"],
                    item["email"] or "",
                    item["role"],
                    item["chat_sessions"],
                    item["chat_messages"],
                    item["notes"],
                    item["flashcards"],
                    item["flashcards_due"],
                    item["flashcards_mastered"],
                    item["quizzes"],
                    item["assigned_quizzes"],
                    item["quiz_attempts"],
                    round(float(item["quiz_avg_score"]) * 100, 2),
                    item["last_activity_at"] or "",
                    item["risk_level"],
                ]
            )
        writer.writerow([])
        writer.writerow(
            [
                "quiz_title",
                "student_count",
                "submission_count",
                "attempt_count",
                "score_avg_percent",
            ]
        )
        for quiz in data["quiz_summary"]:
            writer.writerow(
                [
                    quiz["title"],
                    quiz["student_count"],
                    quiz["submission_count"],
                    quiz["attempt_count"],
                    round(float(quiz["score_avg"]) * 100, 2),
                ]
            )
        return output.getvalue()

    async def assignments(self, user_id: str, course_id: str) -> list[dict[str, Any]]:
        course = await self._get_course(course_id)
        member = await self.require_member(user_id, course_id)
        conditions = [CourseAssignment.course_id == course_id]
        if course.owner_id != user_id and member.role not in {"instructor", "ta"}:
            conditions.append(CourseAssignment.status == "published")
        rows = (
            (
                await self.db.execute(
                    select(CourseAssignment)
                    .where(and_(*conditions))
                    .order_by(desc(CourseAssignment.created_at))
                )
            )
            .scalars()
            .all()
        )
        return [await self._assignment_out(row, user_id) for row in rows]

    async def announcements(self, user_id: str, course_id: str) -> list[dict[str, Any]]:
        course = await self._get_course(course_id)
        member = await self.require_member(user_id, course_id)
        conditions = [CourseAnnouncement.course_id == course_id]
        if course.owner_id != user_id and member.role not in {"instructor", "ta"}:
            conditions.append(CourseAnnouncement.status == "published")
        rows = (
            (
                await self.db.execute(
                    select(CourseAnnouncement)
                    .where(and_(*conditions))
                    .order_by(desc(CourseAnnouncement.created_at))
                )
            )
            .scalars()
            .all()
        )
        return [await self._announcement_out(row, user_id) for row in rows]

    async def create_announcement(
        self,
        user_id: str,
        course_id: str,
        body: CourseAnnouncementCreate,
    ) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        announcement = CourseAnnouncement(
            course_id=course_id,
            created_by=user_id,
            title=body.title,
            content=body.content,
            status=body.status,
        )
        self.db.add(announcement)
        await self.db.commit()
        await self.db.refresh(announcement)
        if announcement.status == "published":
            await self._push_course_event(
                course_id,
                {
                    "type": "course_announcement",
                    "course_id": course_id,
                    "announcement_id": announcement.id,
                    "title": announcement.title,
                },
            )
        return await self._announcement_out(announcement, user_id)

    async def update_announcement(
        self,
        user_id: str,
        course_id: str,
        announcement_id: str,
        body: CourseAnnouncementUpdate,
    ) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        announcement = await self._get_announcement(course_id, announcement_id)
        for field in ("title", "content", "status"):
            if field in body.model_fields_set:
                setattr(announcement, field, getattr(body, field))
        announcement.updated_at = now_iso()
        await self.db.commit()
        await self.db.refresh(announcement)
        return await self._announcement_out(announcement, user_id)

    async def delete_announcement(self, user_id: str, course_id: str, announcement_id: str) -> None:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        announcement = await self._get_announcement(course_id, announcement_id)
        await self.db.delete(announcement)
        await self.db.commit()

    async def mark_announcement_read(
        self, user_id: str, course_id: str, announcement_id: str
    ) -> dict[str, Any]:
        await self.require_member(user_id, course_id)
        announcement = await self._get_announcement(course_id, announcement_id)
        if announcement.status != "published":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
            )
        existing = (
            await self.db.execute(
                select(CourseAnnouncementRead).where(
                    and_(
                        CourseAnnouncementRead.announcement_id == announcement_id,
                        CourseAnnouncementRead.user_id == user_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            self.db.add(CourseAnnouncementRead(announcement_id=announcement_id, user_id=user_id))
        else:
            existing.read_at = now_iso()
        await self.db.commit()
        return {"ok": True}

    async def help_requests(
        self,
        user_id: str,
        course_id: str,
        status_filter: str | None = None,
        priority: str | None = None,
        assigned_to: str | None = None,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        course = await self._get_course(course_id)
        member = await self.require_member(user_id, course_id)
        conditions = [CourseHelpRequest.course_id == course_id]
        if course.owner_id != user_id and member.role not in {"instructor", "ta"}:
            conditions.append(CourseHelpRequest.user_id == user_id)
        if status_filter:
            conditions.append(CourseHelpRequest.status == status_filter)
        if priority:
            conditions.append(CourseHelpRequest.priority == priority)
        if assigned_to == "me":
            conditions.append(CourseHelpRequest.assigned_to == user_id)
        elif assigned_to == "unassigned":
            conditions.append(CourseHelpRequest.assigned_to.is_(None))
        elif assigned_to:
            conditions.append(CourseHelpRequest.assigned_to == assigned_to)
        if q:
            like = f"%{q}%"
            conditions.append(
                or_(CourseHelpRequest.title.ilike(like), CourseHelpRequest.content.ilike(like))
            )
        rows = (
            await self.db.execute(
                select(CourseHelpRequest, User.username)
                .join(User, User.id == CourseHelpRequest.user_id)
                .where(and_(*conditions))
                .order_by(desc(CourseHelpRequest.updated_at))
            )
        ).all()
        return [await self._help_request_out(row, username, user_id) for row, username in rows]

    async def create_help_request(
        self,
        user_id: str,
        course_id: str,
        body: CourseHelpRequestCreate,
    ) -> dict[str, Any]:
        await self.require_member(user_id, course_id)
        if body.session_id:
            session = (
                await self.db.execute(
                    select(ChatSession).where(
                        and_(
                            ChatSession.id == body.session_id,
                            ChatSession.user_id == user_id,
                            ChatSession.course_id == course_id,
                        )
                    )
                )
            ).scalar_one_or_none()
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found"
                )
        request = CourseHelpRequest(
            course_id=course_id,
            user_id=user_id,
            session_id=body.session_id,
            title=body.title,
            content=body.content,
            priority=body.priority,
        )
        self.db.add(request)
        await self.db.flush()
        self.db.add(
            CourseHelpRequestEvent(
                request_id=request.id,
                actor_id=user_id,
                event_type="created",
                message=body.content,
                internal=0,
                to_status="open",
            )
        )
        await self.db.commit()
        await self.db.refresh(request)
        await self._push_course_manager_event(
            course_id,
            {
                "type": "course_help_request",
                "course_id": course_id,
                "help_request_id": request.id,
                "title": request.title,
            },
        )
        username = (
            await self.db.execute(select(User.username).where(User.id == user_id))
        ).scalar_one_or_none()
        return await self._help_request_out(request, username, user_id)

    async def update_help_request(
        self,
        user_id: str,
        course_id: str,
        request_id: str,
        body: CourseHelpRequestUpdate,
    ) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        help_request = await self._get_help_request(course_id, request_id)
        from_status = help_request.status
        event_type = "updated"
        event_assigned_to = None
        if "assigned_to" in body.model_fields_set and body.assigned_to:
            assignee = await self._get_member(course_id, body.assigned_to)
            if assignee.role not in {"instructor", "ta"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Assignee must be instructor or TA",
                )
        if "status" in body.model_fields_set and body.status is not None:
            help_request.status = body.status
            help_request.resolved_at = now_iso() if body.status == "resolved" else None
            event_type = "status_changed"
        if "assigned_to" in body.model_fields_set:
            help_request.assigned_to = body.assigned_to
            event_assigned_to = body.assigned_to
            if event_type == "updated":
                event_type = "assigned"
        if "priority" in body.model_fields_set and body.priority is not None:
            help_request.priority = body.priority
            if event_type == "updated":
                event_type = "priority_changed"
        if "resolution_summary" in body.model_fields_set:
            help_request.resolution_summary = body.resolution_summary
        help_request.updated_at = now_iso()
        if (
            body.comment
            or body.resolution_summary
            or from_status != help_request.status
            or event_assigned_to is not None
        ):
            self.db.add(
                CourseHelpRequestEvent(
                    request_id=help_request.id,
                    actor_id=user_id,
                    event_type=event_type,
                    message=body.comment or body.resolution_summary,
                    internal=1 if body.internal else 0,
                    from_status=from_status if from_status != help_request.status else None,
                    to_status=help_request.status if from_status != help_request.status else None,
                    assigned_to=event_assigned_to,
                )
            )
        await self.db.commit()
        await self.db.refresh(help_request)
        with contextlib.suppress(Exception):
            await push_to_user(
                help_request.user_id,
                {
                    "type": "course_help_update",
                    "course_id": course_id,
                    "help_request_id": help_request.id,
                    "status": help_request.status,
                },
            )
        username = (
            await self.db.execute(select(User.username).where(User.id == help_request.user_id))
        ).scalar_one_or_none()
        return await self._help_request_out(help_request, username, user_id)

    async def create_help_request_comment(
        self,
        user_id: str,
        course_id: str,
        request_id: str,
        message: str,
        internal: bool = False,
    ) -> dict[str, Any]:
        member = await self.require_member(user_id, course_id)
        help_request = await self._get_help_request(course_id, request_id)
        is_manager = member.role in {"instructor", "ta"} or help_request.user_id == user_id
        if not is_manager:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course member only")
        if internal and member.role not in {"instructor", "ta"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager only")
        event = CourseHelpRequestEvent(
            request_id=help_request.id,
            actor_id=user_id,
            event_type="comment",
            message=message,
            internal=1 if internal else 0,
        )
        help_request.updated_at = now_iso()
        self.db.add(event)
        await self.db.commit()
        username = (
            await self.db.execute(select(User.username).where(User.id == help_request.user_id))
        ).scalar_one_or_none()
        return await self._help_request_out(help_request, username, user_id)

    async def question_bank(
        self,
        user_id: str,
        course_id: str,
        status_filter: str | None = None,
        question_type: str | None = None,
        quiz_id: str | None = None,
        q: str | None = None,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        course_quiz_rows = (
            await self.db.execute(
                select(CourseQuiz, Quiz)
                .join(Quiz, Quiz.id == CourseQuiz.quiz_id)
                .where(
                    and_(
                        CourseQuiz.course_id == course_id,
                        CourseQuiz.status.in_(["published", "draft"]),
                    )
                )
                .order_by(desc(CourseQuiz.published_at))
            )
        ).all()
        for course_quiz, quiz in course_quiz_rows:
            await self._ensure_question_bank_items(course_quiz, quiz)
        await self.db.commit()
        conditions = [CourseQuestionBankItem.course_id == course_id]
        if status_filter:
            conditions.append(CourseQuestionBankItem.status == status_filter)
        elif not include_archived:
            conditions.append(CourseQuestionBankItem.status != "archived")
        if question_type:
            conditions.append(CourseQuestionBankItem.question_type == question_type)
        if quiz_id:
            conditions.append(CourseQuestionBankItem.quiz_id == quiz_id)
        if q:
            like = f"%{q}%"
            conditions.append(
                or_(
                    CourseQuestionBankItem.question_json.ilike(like),
                    CourseQuestionBankItem.review_note.ilike(like),
                    Quiz.title.ilike(like),
                    CourseQuiz.title.ilike(like),
                )
            )
        rows = (
            await self.db.execute(
                select(CourseQuestionBankItem, Quiz.title, CourseQuiz.title)
                .join(Quiz, Quiz.id == CourseQuestionBankItem.quiz_id)
                .join(CourseQuiz, CourseQuiz.id == CourseQuestionBankItem.course_quiz_id)
                .where(and_(*conditions))
                .order_by(
                    desc(CourseQuestionBankItem.updated_at), CourseQuestionBankItem.question_index
                )
            )
        ).all()
        return [
            self._question_bank_out(item, quiz_title, course_quiz_title)
            for item, quiz_title, course_quiz_title in rows
        ]

    async def update_question_review(
        self,
        user_id: str,
        course_id: str,
        item_id: str,
        body: CourseQuestionReviewUpdate,
    ) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        row = (
            await self.db.execute(
                select(CourseQuestionBankItem, Quiz.title, CourseQuiz.title)
                .join(Quiz, Quiz.id == CourseQuestionBankItem.quiz_id)
                .join(CourseQuiz, CourseQuiz.id == CourseQuestionBankItem.course_quiz_id)
                .where(
                    and_(
                        CourseQuestionBankItem.id == item_id,
                        CourseQuestionBankItem.course_id == course_id,
                    )
                )
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        item, quiz_title, course_quiz_title = row
        item.status = body.status
        item.review_note = body.review_note
        item.updated_at = now_iso()
        if body.status in {"approved", "rejected"}:
            item.reviewed_by = user_id
            item.reviewed_at = now_iso()
        elif body.status == "draft":
            item.reviewed_by = None
            item.reviewed_at = None
        await self.db.commit()
        return self._question_bank_out(item, quiz_title, course_quiz_title)

    async def update_question_reviews(
        self,
        user_id: str,
        course_id: str,
        body: CourseQuestionReviewBatchUpdate,
    ) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        rows = (
            await self.db.execute(
                select(CourseQuestionBankItem).where(
                    and_(
                        CourseQuestionBankItem.course_id == course_id,
                        CourseQuestionBankItem.id.in_(body.item_ids),
                    )
                )
            )
        ).scalars().all()
        by_id = {row.id: row for row in rows}
        missing = [item_id for item_id in body.item_ids if item_id not in by_id]
        now = now_iso()
        for item in rows:
            item.status = body.status
            item.review_note = body.review_note
            item.updated_at = now
            if body.status in {"approved", "rejected"}:
                item.reviewed_by = user_id
                item.reviewed_at = now
            elif body.status == "draft":
                item.reviewed_by = None
                item.reviewed_at = None
        await self.db.commit()
        return {
            "ok": True,
            "updated": len(rows),
            "missing": missing,
            "status": body.status,
        }

    async def dashboard(self, user_id: str) -> dict[str, Any]:
        course_ids = (
            (
                await self.db.execute(
                    select(CourseMember.course_id)
                    .join(Course, Course.id == CourseMember.course_id)
                    .where(and_(CourseMember.user_id == user_id, Course.is_active == 1))
                )
            )
            .scalars()
            .all()
        )
        if not course_ids:
            return {"announcements": [], "help_requests": [], "managed_help_count": 0}
        announcements = (
            await self.db.execute(
                select(CourseAnnouncement, Course.title)
                .join(Course, Course.id == CourseAnnouncement.course_id)
                .where(
                    and_(
                        CourseAnnouncement.course_id.in_(course_ids),
                        CourseAnnouncement.status == "published",
                        ~CourseAnnouncement.id.in_(
                            select(CourseAnnouncementRead.announcement_id).where(
                                CourseAnnouncementRead.user_id == user_id
                            )
                        ),
                    )
                )
                .order_by(desc(CourseAnnouncement.created_at))
                .limit(8)
            )
        ).all()
        managed_course_ids = await self._managed_course_ids(user_id)
        help_rows = []
        if managed_course_ids:
            help_rows = (
                await self.db.execute(
                    select(CourseHelpRequest, Course.title, User.username)
                    .join(Course, Course.id == CourseHelpRequest.course_id)
                    .join(User, User.id == CourseHelpRequest.user_id)
                    .where(
                        and_(
                            CourseHelpRequest.course_id.in_(managed_course_ids),
                            CourseHelpRequest.status.in_(["open", "in_progress"]),
                        )
                    )
                    .order_by(desc(CourseHelpRequest.updated_at))
                    .limit(8)
                )
            ).all()
        return {
            "announcements": [
                {
                    **await self._announcement_out(announcement, user_id),
                    "course_title": course_title,
                }
                for announcement, course_title in announcements
            ],
            "help_requests": [
                {
                    **await self._help_request_out(help_request, username, user_id),
                    "course_title": course_title,
                }
                for help_request, course_title, username in help_rows
            ],
            "managed_help_count": len(help_rows),
        }

    async def create_assignment(
        self,
        user_id: str,
        course_id: str,
        body: CourseAssignmentCreate,
    ) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        await self._validate_assignment_refs(
            user_id, course_id, body.kind, body.doc_id, body.quiz_id
        )
        assignment = CourseAssignment(
            course_id=course_id,
            created_by=user_id,
            title=body.title,
            description=body.description,
            kind=body.kind,
            doc_id=body.doc_id,
            quiz_id=body.quiz_id,
            due_at=body.due_at,
            status=body.status,
        )
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        return await self._assignment_out(assignment, user_id)

    async def update_assignment(
        self,
        user_id: str,
        course_id: str,
        assignment_id: str,
        body: CourseAssignmentUpdate,
    ) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        assignment = await self._get_assignment(course_id, assignment_id)
        next_kind = body.kind if body.kind is not None else assignment.kind
        next_doc_id = body.doc_id if "doc_id" in body.model_fields_set else assignment.doc_id
        next_quiz_id = body.quiz_id if "quiz_id" in body.model_fields_set else assignment.quiz_id
        await self._validate_assignment_refs(
            user_id, course_id, next_kind, next_doc_id, next_quiz_id
        )
        for field in ("title", "description", "kind", "doc_id", "quiz_id", "due_at", "status"):
            if field in body.model_fields_set:
                setattr(assignment, field, getattr(body, field))
        await self.db.commit()
        await self.db.refresh(assignment)
        return await self._assignment_out(assignment, user_id)

    async def delete_assignment(self, user_id: str, course_id: str, assignment_id: str) -> None:
        await self.require_role(user_id, course_id, {"instructor", "ta"})
        assignment = await self._get_assignment(course_id, assignment_id)
        await self.db.delete(assignment)
        await self.db.commit()

    async def submit_assignment(
        self,
        user_id: str,
        course_id: str,
        assignment_id: str,
        body: CourseAssignmentSubmit,
    ) -> dict[str, Any]:
        await self.require_member(user_id, course_id)
        assignment = await self._get_assignment(course_id, assignment_id)
        if assignment.status != "published":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
            )
        existing = (
            await self.db.execute(
                select(CourseAssignmentSubmission)
                .where(
                    and_(
                        CourseAssignmentSubmission.assignment_id == assignment_id,
                        CourseAssignmentSubmission.user_id == user_id,
                    )
                )
                .order_by(desc(CourseAssignmentSubmission.submitted_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if existing is None:
            submission = CourseAssignmentSubmission(
                assignment_id=assignment_id,
                user_id=user_id,
                response=body.response,
            )
            self.db.add(submission)
        else:
            existing.response = body.response
            existing.status = "completed"
            existing.submitted_at = now_iso()
        await self.db.commit()
        return await self._assignment_out(assignment, user_id)

    async def course_document_ids(self, user_id: str, course_id: str) -> list[str]:
        await self._get_course(course_id)
        await self.require_member(user_id, course_id)
        rows = (
            (
                await self.db.execute(
                    select(CourseDocument.doc_id)
                    .join(Document, Document.id == CourseDocument.doc_id)
                    .where(
                        and_(
                            CourseDocument.course_id == course_id,
                            CourseDocument.is_active == 1,
                            Document.status == "ready",
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
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

    async def require_role(self, user_id: str, course_id: str, roles: set[str]) -> CourseMember:
        course = await self._get_course(course_id)
        member = await self.require_member(user_id, course_id)
        if course.owner_id == user_id:
            return member
        if member.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient course role"
            )
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course member not found"
            )
        return member

    async def _get_assignment(self, course_id: str, assignment_id: str) -> CourseAssignment:
        assignment = (
            await self.db.execute(
                select(CourseAssignment).where(
                    and_(
                        CourseAssignment.id == assignment_id,
                        CourseAssignment.course_id == course_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found"
            )
        return assignment

    async def _get_announcement(self, course_id: str, announcement_id: str) -> CourseAnnouncement:
        announcement = (
            await self.db.execute(
                select(CourseAnnouncement).where(
                    and_(
                        CourseAnnouncement.id == announcement_id,
                        CourseAnnouncement.course_id == course_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if announcement is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found"
            )
        return announcement

    async def _get_help_request(self, course_id: str, request_id: str) -> CourseHelpRequest:
        help_request = (
            await self.db.execute(
                select(CourseHelpRequest).where(
                    and_(
                        CourseHelpRequest.id == request_id,
                        CourseHelpRequest.course_id == course_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if help_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Help request not found"
            )
        return help_request

    async def _validate_assignment_refs(
        self,
        user_id: str,
        course_id: str,
        kind: str,
        doc_id: str | None,
        quiz_id: str | None,
    ) -> None:
        if kind in {"read_summary", "note", "flashcards"} and not doc_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Document is required"
            )
        if kind == "quiz" and not quiz_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz is required")
        if doc_id:
            course_doc = (
                await self.db.execute(
                    select(CourseDocument)
                    .join(Document, Document.id == CourseDocument.doc_id)
                    .where(
                        and_(
                            CourseDocument.course_id == course_id,
                            CourseDocument.doc_id == doc_id,
                            CourseDocument.is_active == 1,
                            Document.status == "ready",
                        )
                    )
                )
            ).scalar_one_or_none()
            if course_doc is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Document must be shared with this course first",
                )
        if quiz_id:
            course_quiz = (
                await self.db.execute(
                    select(CourseQuiz).where(
                        and_(
                            CourseQuiz.course_id == course_id,
                            CourseQuiz.quiz_id == quiz_id,
                            CourseQuiz.status == "published",
                        )
                    )
                )
            ).scalar_one_or_none()
            if course_quiz is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quiz must be published to this course first",
                )

    async def _assignment_out(self, assignment: CourseAssignment, user_id: str) -> dict[str, Any]:
        doc_filename = None
        quiz_title = None
        if assignment.doc_id:
            doc_filename = (
                await self.db.execute(
                    select(Document.filename).where(Document.id == assignment.doc_id)
                )
            ).scalar_one_or_none()
        if assignment.quiz_id:
            quiz_title = (
                await self.db.execute(select(Quiz.title).where(Quiz.id == assignment.quiz_id))
            ).scalar_one_or_none()
        return {
            "id": assignment.id,
            "course_id": assignment.course_id,
            "created_by": assignment.created_by,
            "title": assignment.title,
            "description": assignment.description,
            "kind": assignment.kind,
            "doc_id": assignment.doc_id,
            "doc_filename": doc_filename,
            "quiz_id": assignment.quiz_id,
            "quiz_title": quiz_title,
            "due_at": assignment.due_at,
            "status": assignment.status,
            "created_at": assignment.created_at,
            "completion": await self._assignment_completion(assignment, user_id),
        }

    async def _announcement_out(
        self, announcement: CourseAnnouncement, user_id: str
    ) -> dict[str, Any]:
        read = (
            await self.db.execute(
                select(CourseAnnouncementRead).where(
                    and_(
                        CourseAnnouncementRead.announcement_id == announcement.id,
                        CourseAnnouncementRead.user_id == user_id,
                    )
                )
            )
        ).scalar_one_or_none()
        username = (
            await self.db.execute(select(User.username).where(User.id == announcement.created_by))
        ).scalar_one_or_none()
        return {
            "id": announcement.id,
            "course_id": announcement.course_id,
            "created_by": announcement.created_by,
            "created_by_username": username,
            "title": announcement.title,
            "content": announcement.content,
            "status": announcement.status,
            "read_at": read.read_at if read else None,
            "created_at": announcement.created_at,
            "updated_at": announcement.updated_at,
        }

    async def _help_request_out(
        self,
        help_request: CourseHelpRequest,
        username: str | None,
        viewer_id: str | None = None,
    ) -> dict[str, Any]:
        session_messages = await self._help_request_session_messages(help_request)
        assignee_username = None
        if help_request.assigned_to:
            assignee_username = (
                await self.db.execute(select(User.username).where(User.id == help_request.assigned_to))
            ).scalar_one_or_none()
        events = await self._help_request_events(help_request, viewer_id)
        return {
            "id": help_request.id,
            "course_id": help_request.course_id,
            "user_id": help_request.user_id,
            "username": username,
            "session_id": help_request.session_id,
            "assigned_to": help_request.assigned_to,
            "assigned_to_username": assignee_username,
            "title": help_request.title,
            "content": help_request.content,
            "status": help_request.status,
            "priority": help_request.priority,
            "resolved_at": help_request.resolved_at,
            "resolution_summary": help_request.resolution_summary,
            "created_at": help_request.created_at,
            "updated_at": help_request.updated_at,
            "session_messages": session_messages,
            "events": events,
        }

    async def _help_request_events(
        self,
        help_request: CourseHelpRequest,
        viewer_id: str | None,
    ) -> list[dict[str, Any]]:
        can_view_internal = False
        if viewer_id:
            member = (
                await self.db.execute(
                    select(CourseMember).where(
                        and_(
                            CourseMember.course_id == help_request.course_id,
                            CourseMember.user_id == viewer_id,
                        )
                    )
                )
            ).scalar_one_or_none()
            can_view_internal = bool(member and member.role in {"instructor", "ta"})
        conditions = [CourseHelpRequestEvent.request_id == help_request.id]
        if not can_view_internal:
            conditions.append(CourseHelpRequestEvent.internal == 0)
        rows = (
            await self.db.execute(
                select(CourseHelpRequestEvent, User.username)
                .outerjoin(User, User.id == CourseHelpRequestEvent.actor_id)
                .where(and_(*conditions))
                .order_by(CourseHelpRequestEvent.created_at)
            )
        ).all()
        return [
            {
                "id": event.id,
                "actor_id": event.actor_id,
                "actor_username": actor_username,
                "event_type": event.event_type,
                "message": event.message,
                "internal": bool(event.internal),
                "from_status": event.from_status,
                "to_status": event.to_status,
                "assigned_to": event.assigned_to,
                "created_at": event.created_at,
            }
            for event, actor_username in rows
        ]

    async def _help_request_session_messages(
        self,
        help_request: CourseHelpRequest,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        if not help_request.session_id:
            return []
        session = (
            await self.db.execute(
                select(ChatSession).where(
                    and_(
                        ChatSession.id == help_request.session_id,
                        ChatSession.user_id == help_request.user_id,
                        ChatSession.course_id == help_request.course_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if session is None:
            return []
        messages = (
            (
                await self.db.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session.id)
                    .order_by(desc(ChatMessage.created_at))
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at,
            }
            for message in reversed(messages)
        ]

    async def _ensure_question_bank_items(self, course_quiz: CourseQuiz, quiz: Quiz) -> None:
        existing_items = (
            (
                await self.db.execute(
                    select(CourseQuestionBankItem).where(
                        and_(
                            CourseQuestionBankItem.course_id == course_quiz.course_id,
                            CourseQuestionBankItem.quiz_id == quiz.id,
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        by_index = {item.question_index: item for item in existing_items}
        questions = _safe_json_list(quiz.questions)
        seen_indexes: set[int] = set()
        for index, question in enumerate(questions):
            seen_indexes.add(index)
            question_json = json.dumps(question, ensure_ascii=False)
            question_type = str(question.get("type") or question.get("kind") or "").strip() or None
            item = by_index.get(index)
            if item is None:
                self.db.add(
                    CourseQuestionBankItem(
                        course_id=course_quiz.course_id,
                        course_quiz_id=course_quiz.id,
                        quiz_id=quiz.id,
                        question_index=index,
                        question_type=question_type,
                        question_json=question_json,
                        created_by=course_quiz.created_by,
                        status="approved",
                        reviewed_by=course_quiz.created_by,
                        reviewed_at=now_iso(),
                    )
                )
            else:
                item.course_quiz_id = course_quiz.id
                item.question_type = question_type
                item.question_json = question_json
                if item.status == "draft":
                    item.status = "approved"
                    item.reviewed_by = course_quiz.created_by
                    item.reviewed_at = now_iso()
                item.updated_at = now_iso()
        for item in existing_items:
            if item.question_index not in seen_indexes and item.status != "archived":
                item.status = "archived"
                item.updated_at = now_iso()

    def _question_bank_out(
        self,
        item: CourseQuestionBankItem,
        quiz_title: str,
        course_quiz_title: str,
    ) -> dict[str, Any]:
        try:
            question = json.loads(item.question_json)
        except json.JSONDecodeError:
            question = {}
        return {
            "id": item.id,
            "course_id": item.course_id,
            "course_quiz_id": item.course_quiz_id,
            "quiz_id": item.quiz_id,
            "quiz_title": quiz_title,
            "course_quiz_title": course_quiz_title,
            "question_index": item.question_index,
            "question_type": item.question_type,
            "question": question,
            "status": item.status,
            "review_note": item.review_note,
            "created_by": item.created_by,
            "reviewed_by": item.reviewed_by,
            "reviewed_at": item.reviewed_at,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }

    async def _assignment_completion(
        self,
        assignment: CourseAssignment,
        user_id: str,
    ) -> dict[str, Any]:
        completed_at: str | None = None
        source: str | None = None
        score: float | None = None
        manual = (
            await self.db.execute(
                select(CourseAssignmentSubmission)
                .where(
                    and_(
                        CourseAssignmentSubmission.assignment_id == assignment.id,
                        CourseAssignmentSubmission.user_id == user_id,
                    )
                )
                .order_by(desc(CourseAssignmentSubmission.submitted_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if manual:
            completed_at = manual.submitted_at
            source = "manual"
            score = manual.score
        if assignment.kind == "quiz" and assignment.quiz_id:
            attempt = (
                await self.db.execute(
                    select(QuizAttempt)
                    .where(
                        and_(
                            QuizAttempt.user_id == user_id,
                            QuizAttempt.quiz_id == assignment.quiz_id,
                        )
                    )
                    .order_by(desc(QuizAttempt.completed_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if attempt:
                completed_at = attempt.completed_at
                source = "quiz"
                score = attempt.total_score
        elif assignment.kind == "read_summary" and assignment.doc_id:
            artifact = (
                await self.db.execute(
                    select(LearningArtifact)
                    .where(
                        and_(
                            LearningArtifact.user_id == user_id,
                            LearningArtifact.doc_id == assignment.doc_id,
                            LearningArtifact.kind == "summary",
                        )
                    )
                    .order_by(desc(LearningArtifact.created_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if artifact:
                completed_at = artifact.created_at
                source = "summary"
        elif assignment.kind == "note" and assignment.doc_id:
            note = (
                await self.db.execute(
                    select(Note)
                    .where(and_(Note.user_id == user_id, Note.doc_id == assignment.doc_id))
                    .order_by(desc(Note.created_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if note:
                completed_at = note.created_at
                source = "note"
        elif assignment.kind == "flashcards" and assignment.doc_id:
            card = (
                await self.db.execute(
                    select(Flashcard)
                    .where(
                        and_(Flashcard.user_id == user_id, Flashcard.doc_id == assignment.doc_id)
                    )
                    .order_by(desc(Flashcard.created_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if card:
                completed_at = card.created_at
                source = "flashcards"
        is_late = bool(
            completed_at and assignment.due_at and _is_after(completed_at, assignment.due_at)
        )
        if completed_at:
            completion_status = "late" if is_late else "completed"
        elif assignment.due_at and _is_past(assignment.due_at):
            completion_status = "overdue"
        else:
            completion_status = "pending"
        return {
            "status": completion_status,
            "completed_at": completed_at,
            "source": source,
            "is_late": is_late,
            "score": score,
        }

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
            "join_code": course.join_code
            if course.owner_id == user_id or member.role in {"instructor", "ta"}
            else None,
            "role": member.role,
            "is_active": course.is_active,
            "created_at": course.created_at,
        }
        if include_detail:
            doc_conditions = [CourseDocument.course_id == course.id]
            if course.owner_id != user_id and member.role not in {"instructor", "ta"}:
                doc_conditions.extend([CourseDocument.is_active == 1, Document.status == "ready"])
            docs = (
                await self.db.execute(
                    select(Document, CourseDocument, User.username)
                    .join(CourseDocument, CourseDocument.doc_id == Document.id)
                    .outerjoin(User, User.id == CourseDocument.added_by)
                    .where(and_(*doc_conditions))
                    .order_by(desc(CourseDocument.added_at))
                )
            ).all()
            data["documents"] = [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "status": doc.status,
                    "course_status": "active" if course_doc.is_active else "removed",
                    "page_count": doc.page_count,
                    "chunk_count": doc.chunk_count,
                    "created_at": doc.created_at,
                    "added_at": course_doc.added_at,
                    "removed_at": course_doc.removed_at,
                    "added_by": course_doc.added_by,
                    "added_by_username": added_by_username,
                    "version_label": course_doc.version_label,
                    "note": course_doc.note,
                }
                for doc, course_doc, added_by_username in docs
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create join code"
        )

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
                (
                    await self.db.execute(
                        select(QuizAttempt).where(
                            and_(
                                QuizAttempt.quiz_id == quiz.id, QuizAttempt.user_id.in_(student_ids)
                            )
                        )
                    )
                )
                .scalars()
                .all()
                if student_ids
                else []
            )
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

    async def _managed_course_ids(self, user_id: str) -> list[str]:
        rows = (
            (
                await self.db.execute(
                    select(Course.id)
                    .join(CourseMember, CourseMember.course_id == Course.id)
                    .where(
                        and_(
                            CourseMember.user_id == user_id,
                            CourseMember.role.in_(["instructor", "ta"]),
                            Course.is_active == 1,
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        owned = (
            (
                await self.db.execute(
                    select(Course.id).where(and_(Course.owner_id == user_id, Course.is_active == 1))
                )
            )
            .scalars()
            .all()
        )
        return sorted(set(rows).union(owned))

    async def _push_course_event(self, course_id: str, message: dict[str, Any]) -> None:
        member_ids = (
            (
                await self.db.execute(
                    select(CourseMember.user_id).where(CourseMember.course_id == course_id)
                )
            )
            .scalars()
            .all()
        )
        for member_id in member_ids:
            with contextlib.suppress(Exception):
                await push_to_user(member_id, message)

    async def _push_course_manager_event(self, course_id: str, message: dict[str, Any]) -> None:
        course = await self._get_course(course_id)
        rows = (
            (
                await self.db.execute(
                    select(CourseMember.user_id).where(
                        and_(
                            CourseMember.course_id == course_id,
                            CourseMember.role.in_(["instructor", "ta"]),
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        manager_ids = set(rows)
        manager_ids.add(course.owner_id)
        for manager_id in manager_ids:
            with contextlib.suppress(Exception):
                await push_to_user(manager_id, message)


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


def _course_document_ids(body: CourseDocumentRequest) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    raw_ids = ([body.doc_id] if body.doc_id else []) + body.doc_ids
    for doc_id in raw_ids:
        if doc_id not in seen:
            seen.add(doc_id)
            result.append(doc_id)
    return result


def _answers_match(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return str(actual).strip() == str(expected).strip()


def _item_analysis(
    questions: list[dict[str, Any]], attempts: list[QuizAttempt]
) -> list[dict[str, Any]]:
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


def _parse_datetime(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_after(left: str, right: str) -> bool:
    try:
        return _parse_datetime(left) > _parse_datetime(right)
    except ValueError:
        return left > right


def _is_past(value: str) -> bool:
    try:
        return _parse_datetime(value) < datetime.now(UTC)
    except ValueError:
        return value < now_iso()
