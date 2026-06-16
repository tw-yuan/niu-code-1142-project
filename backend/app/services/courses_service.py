from __future__ import annotations

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
    Document,
    Flashcard,
    Note,
    Quiz,
    User,
)
from app.schemas import CourseCreate, CourseDocumentRequest, CourseJoinRequest
from app.services.json_utils import from_json_list


class CoursesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, body: CourseCreate) -> dict[str, Any]:
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
        await self.require_role(user_id, course_id, {"instructor"})
        doc = (
            await self.db.execute(
                select(Document).where(and_(Document.id == body.doc_id, Document.user_id == user_id))
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
        await self.require_role(user_id, course_id, {"instructor"})
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

    async def members(self, user_id: str, course_id: str) -> list[dict[str, Any]]:
        await self.require_member(user_id, course_id)
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
                "email": email,
                "role": member.role,
                "joined_at": member.joined_at,
            }
            for member, username, email in rows
        ]

    async def progress(self, user_id: str, course_id: str) -> dict[str, Any]:
        await self.require_role(user_id, course_id, {"instructor"})
        doc_ids = await self.course_document_ids(user_id, course_id)
        members = await self.members(user_id, course_id)
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
            flashcard_count = 0
            quiz_count = 0
            if doc_ids:
                note_count = (
                    await self.db.execute(
                        select(func.count(Note.id)).where(and_(Note.user_id == member_id, Note.doc_id.in_(doc_ids)))
                    )
                ).scalar_one()
                flashcard_count = (
                    await self.db.execute(
                        select(func.count(Flashcard.id)).where(
                            and_(Flashcard.user_id == member_id, Flashcard.doc_id.in_(doc_ids))
                        )
                    )
                ).scalar_one()
                quizzes = (
                    await self.db.execute(select(Quiz).where(Quiz.user_id == member_id))
                ).scalars().all()
                quiz_count = sum(1 for quiz in quizzes if set(from_json_list(quiz.doc_ids)) & set(doc_ids))
            rows.append(
                {
                    **member,
                    "chat_sessions": len(chat_sessions),
                    "chat_messages": int(message_count),
                    "notes": int(note_count),
                    "flashcards": int(flashcard_count),
                    "quizzes": int(quiz_count),
                    "last_activity_at": chat_sessions[0].updated_at if chat_sessions else None,
                }
            )
        return {"course_id": course_id, "document_count": len(doc_ids), "students": rows}

    async def course_document_ids(self, user_id: str, course_id: str) -> list[str]:
        await self._get_course(course_id)
        await self.require_member(user_id, course_id)
        rows = (
            await self.db.execute(
                select(CourseDocument.doc_id).where(CourseDocument.course_id == course_id)
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
            "join_code": course.join_code if course.owner_id == user_id or member.role == "instructor" else None,
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
