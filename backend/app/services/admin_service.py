import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import and_, desc, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import (
    AdminConfig,
    ChatMessage,
    ChatSession,
    Course,
    CourseDocument,
    CourseMember,
    Document,
    Quiz,
    SystemEvent,
    TokenUsage,
    User,
    now_iso,
)
from app.schemas import (
    AdminConfigUpdate,
    AdminCourseMemberUpdate,
    AdminCourseUpdate,
    AdminPasswordReset,
    AdminUserCreate,
    AdminUserUpdate,
    CourseDocumentRequest,
)
from app.services.audit_service import AuditService
from app.services.chroma_service import ChromaService
from app.services.cost_service import cost_stats
from app.services.json_utils import from_json_list, to_json
from app.services.privacy_service import PrivacyService
from app.services.security import hash_password
from app.services.storage import remove_document_dir


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        q: str | None = None,
        role: str | None = None,
        is_active: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions = []
        if q:
            like = f"%{q}%"
            conditions.append(or_(User.username.ilike(like), User.email.ilike(like)))
        if role:
            conditions.append(User.role == role)
        if is_active is not None:
            conditions.append(User.is_active == is_active)

        stmt = select(User)
        count_stmt = select(func.count(User.id))
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        users = (
            await self.db.execute(
                stmt.order_by(desc(User.created_at)).limit(limit).offset(offset)
            )
        ).scalars().all()
        total = (await self.db.execute(count_stmt)).scalar_one()
        usage_by_user = await self._usage_by_user([user.id for user in users])
        document_stats = await self._document_stats([user.id for user in users])
        return {
            "items": [
                self._user_summary(user, usage_by_user.get(user.id, 0), document_stats.get(user.id, {}))
                for user in users
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def create_user(
        self,
        body: AdminUserCreate,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        existing = (
            await self.db.execute(
                select(User).where(or_(User.username == body.username, User.email == body.email))
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
        user = User(
            username=body.username,
            email=body.email,
            password_hash=hash_password(body.password),
            role=body.role,
            quota_mb=body.quota_mb,
            token_quota=body.token_quota,
            is_active=body.is_active,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        await AuditService(self.db).log(
            "admin.user_create",
            user_id=actor_id,
            resource=f"user:{user.id}",
            detail=body.model_dump(exclude={"password"}),
        )
        return self._user_summary(user, 0, {})

    async def update_user(self, user_id: str, body: AdminUserUpdate, actor_id: str | None = None) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        next_role = body.role if body.role is not None else user.role
        next_active = body.is_active if body.is_active is not None else user.is_active
        if actor_id == user.id and user.role == "admin" and (next_role != "admin" or not next_active):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot disable or demote your own admin account",
            )
        if user.role == "admin" and (next_role != "admin" or not next_active):
            await self._ensure_another_active_admin(user.id)
        conflict_filters = []
        if body.username and body.username != user.username:
            conflict_filters.append(User.username == body.username)
        if body.email and body.email != user.email:
            conflict_filters.append(User.email == body.email)
        if conflict_filters:
            existing = (
                await self.db.execute(
                    select(User).where(and_(User.id != user_id, or_(*conflict_filters)))
                )
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")
        for field in ("username", "email", "quota_mb", "token_quota", "is_active", "role"):
            value = getattr(body, field)
            if value is not None:
                setattr(user, field, value)
        await self.db.commit()
        await self.db.refresh(user)
        await AuditService(self.db).log(
            "admin.user_update",
            user_id=actor_id,
            resource=f"user:{user_id}",
            detail=body.model_dump(exclude_none=True),
        )
        usage_by_user = await self._usage_by_user([user.id])
        document_stats = await self._document_stats([user.id])
        return self._user_summary(user, usage_by_user.get(user.id, 0), document_stats.get(user.id, {}))

    async def reset_user_password(
        self,
        user_id: str,
        body: AdminPasswordReset,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user.password_hash = hash_password(body.password)
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.user_password_reset",
            user_id=actor_id,
            resource=f"user:{user_id}",
        )
        return {"ok": True}

    async def user_detail(self, user_id: str) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        usage_by_user = await self._usage_by_user([user.id])
        document_stats = await self._document_stats([user.id])
        data = self._user_summary(user, usage_by_user.get(user.id, 0), document_stats.get(user.id, {}))
        data["usage"] = await self.user_usage(user_id)
        data["recent_audit_logs"] = await AuditService(self.db).list_logs(user_id=user_id, limit=20)
        data["deletion"] = {
            "requested_at": user.deletion_requested_at,
            "scheduled_at": user.deletion_scheduled_at,
            "export_expires_at": user.export_expires_at,
        }
        return data

    async def user_usage(self, user_id: str) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        now = datetime.now(UTC)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        since_30 = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=29)
        rows = (
            await self.db.execute(
                select(TokenUsage)
                .where(and_(TokenUsage.user_id == user_id, TokenUsage.created_at >= since_30.isoformat()))
                .order_by(desc(TokenUsage.created_at))
            )
        ).scalars().all()
        by_feature: dict[str, int] = {}
        by_model: dict[str, int] = {}
        daily: dict[str, int] = {}
        month_total = 0
        for row in rows:
            created = datetime.fromisoformat(row.created_at)
            if created >= month_start:
                month_total += row.tokens_used
                by_feature[row.feature] = by_feature.get(row.feature, 0) + row.tokens_used
                by_model[row.model] = by_model.get(row.model, 0) + row.tokens_used
            day = row.created_at[:10]
            daily[day] = daily.get(day, 0) + row.tokens_used
        series = []
        for i in range(30):
            day = (since_30 + timedelta(days=i)).date().isoformat()
            series.append({"date": day, "tokens": daily.get(day, 0)})
        return {
            "token_used_this_month": month_total,
            "token_quota": user.token_quota,
            "quota_percent": int(month_total / user.token_quota * 100) if user.token_quota else 100,
            "by_feature": by_feature,
            "by_model": by_model,
            "daily_series": series,
            "recent_events": [
                {
                    "id": row.id,
                    "feature": row.feature,
                    "model": row.model,
                    "tokens_used": row.tokens_used,
                    "created_at": row.created_at,
                }
                for row in rows[:30]
            ],
        }

    async def list_documents(
        self,
        q: str | None = None,
        user_id: str | None = None,
        status_value: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions = []
        if q:
            conditions.append(Document.filename.ilike(f"%{q}%"))
        if user_id:
            conditions.append(Document.user_id == user_id)
        if status_value:
            conditions.append(Document.status == status_value)
        stmt = select(Document, User.username, User.email).join(User, User.id == Document.user_id)
        count_stmt = select(func.count(Document.id))
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        rows = (
            await self.db.execute(
                stmt.order_by(desc(Document.created_at)).limit(limit).offset(offset)
            )
        ).all()
        total = (await self.db.execute(count_stmt)).scalar_one()
        return {
            "items": [
                {
                    "id": doc.id,
                    "user_id": doc.user_id,
                    "username": username,
                    "email": email,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "status": doc.status,
                    "page_count": doc.page_count,
                    "chunk_count": doc.chunk_count,
                    "error_msg": doc.error_msg,
                    "created_at": doc.created_at,
                    "updated_at": doc.updated_at,
                }
                for doc, username, email in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def delete_document(
        self,
        doc_id: str,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        doc = (await self.db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        user_id = doc.user_id
        filename = doc.filename
        await ChromaService().delete_doc_chunks(user_id, doc_id)
        await self._remove_document_references(doc_id)
        await self.db.delete(doc)
        await self.db.commit()
        remove_document_dir(user_id, doc_id)
        await AuditService(self.db).log(
            "admin.document_delete",
            user_id=actor_id,
            resource=f"document:{doc_id}",
            request=request,
            detail={"owner_id": user_id, "filename": filename},
        )
        return {"ok": True}

    async def list_chat_sessions(
        self,
        q: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions = []
        if q:
            conditions.append(ChatSession.title.ilike(f"%{q}%"))
        if user_id:
            conditions.append(ChatSession.user_id == user_id)
        stmt = (
            select(ChatSession, User.username, func.count(ChatMessage.id))
            .join(User, User.id == ChatSession.user_id)
            .outerjoin(ChatMessage, ChatMessage.session_id == ChatSession.id)
            .group_by(ChatSession.id, User.username)
        )
        count_stmt = select(func.count(ChatSession.id))
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        rows = (
            await self.db.execute(
                stmt.order_by(desc(ChatSession.updated_at)).limit(limit).offset(offset)
            )
        ).all()
        total = (await self.db.execute(count_stmt)).scalar_one()
        return {
            "items": [
                {
                    "id": session.id,
                    "user_id": session.user_id,
                    "username": username,
                    "title": session.title,
                    "doc_ids": from_json_list(session.doc_ids),
                    "course_id": session.course_id,
                    "mode": session.mode,
                    "message_count": int(message_count),
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                }
                for session, username, message_count in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def chat_session_detail(
        self,
        session_id: str,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        row = (
            await self.db.execute(
                select(ChatSession, User.username)
                .join(User, User.id == ChatSession.user_id)
                .where(ChatSession.id == session_id)
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
        session, username = row
        await AuditService(self.db).log(
            "admin.chat_view",
            user_id=actor_id,
            resource=f"chat_session:{session_id}",
            request=request,
            detail={"owner_id": session.user_id},
        )
        messages = (
            await self.db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.created_at)
            )
        ).scalars().all()
        return {
            "id": session.id,
            "user_id": session.user_id,
            "username": username,
            "title": session.title,
            "doc_ids": from_json_list(session.doc_ids),
            "course_id": session.course_id,
            "mode": session.mode,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "citations": from_json_list(message.citations),
                    "token_count": message.token_count,
                    "created_at": message.created_at,
                }
                for message in messages
            ],
        }

    async def delete_chat_session(
        self,
        session_id: str,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        session = (
            await self.db.execute(select(ChatSession).where(ChatSession.id == session_id))
        ).scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
        owner_id = session.user_id
        await self.db.delete(session)
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.chat_delete",
            user_id=actor_id,
            resource=f"chat_session:{session_id}",
            request=request,
            detail={"owner_id": owner_id},
        )
        return {"ok": True}

    async def list_courses(
        self,
        q: str | None = None,
        owner_id: str | None = None,
        is_active: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        conditions = []
        if q:
            conditions.append(Course.title.ilike(f"%{q}%"))
        if owner_id:
            conditions.append(Course.owner_id == owner_id)
        if is_active is not None:
            conditions.append(Course.is_active == is_active)
        stmt = (
            select(
                Course,
                User.username,
                func.count(distinct(CourseMember.user_id)),
                func.count(distinct(CourseDocument.doc_id)),
            )
            .join(User, User.id == Course.owner_id)
            .outerjoin(CourseMember, CourseMember.course_id == Course.id)
            .outerjoin(CourseDocument, CourseDocument.course_id == Course.id)
            .group_by(Course.id, User.username)
        )
        count_stmt = select(func.count(Course.id))
        if conditions:
            stmt = stmt.where(and_(*conditions))
            count_stmt = count_stmt.where(and_(*conditions))
        rows = (
            await self.db.execute(
                stmt.order_by(desc(Course.created_at)).limit(limit).offset(offset)
            )
        ).all()
        total = (await self.db.execute(count_stmt)).scalar_one()
        return {
            "items": [
                {
                    "id": course.id,
                    "owner_id": course.owner_id,
                    "owner_username": owner_username,
                    "title": course.title,
                    "description": course.description,
                    "join_code": course.join_code,
                    "is_active": course.is_active,
                    "member_count": int(member_count),
                    "document_count": int(document_count),
                    "created_at": course.created_at,
                }
                for course, owner_username, member_count, document_count in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    async def course_detail(self, course_id: str) -> dict[str, Any]:
        row = (
            await self.db.execute(
                select(Course, User.username)
                .join(User, User.id == Course.owner_id)
                .where(Course.id == course_id)
            )
        ).one_or_none()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        course, owner_username = row
        members = (
            await self.db.execute(
                select(CourseMember, User.username, User.email)
                .join(User, User.id == CourseMember.user_id)
                .where(CourseMember.course_id == course_id)
                .order_by(CourseMember.joined_at)
            )
        ).all()
        docs = (
            await self.db.execute(
                select(Document, User.username)
                .join(CourseDocument, CourseDocument.doc_id == Document.id)
                .join(User, User.id == Document.user_id)
                .where(CourseDocument.course_id == course_id)
                .order_by(desc(CourseDocument.added_at))
            )
        ).all()
        return {
            "id": course.id,
            "owner_id": course.owner_id,
            "owner_username": owner_username,
            "title": course.title,
            "description": course.description,
            "join_code": course.join_code,
            "is_active": course.is_active,
            "created_at": course.created_at,
            "members": [
                {
                    "user_id": member.user_id,
                    "username": username,
                    "email": email,
                    "role": member.role,
                    "joined_at": member.joined_at,
                }
                for member, username, email in members
            ],
            "documents": [
                {
                    "id": doc.id,
                    "user_id": doc.user_id,
                    "username": username,
                    "filename": doc.filename,
                    "status": doc.status,
                    "page_count": doc.page_count,
                    "chunk_count": doc.chunk_count,
                    "created_at": doc.created_at,
                }
                for doc, username in docs
            ],
        }

    async def update_course(
        self,
        course_id: str,
        body: AdminCourseUpdate,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        course = (await self.db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        for field in ("title", "description", "is_active"):
            value = getattr(body, field)
            if value is not None:
                setattr(course, field, value)
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.course_update",
            user_id=actor_id,
            resource=f"course:{course_id}",
            request=request,
            detail=body.model_dump(exclude_none=True),
        )
        return await self.course_detail(course_id)

    async def delete_course(
        self,
        course_id: str,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        course = (await self.db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        await self.db.delete(course)
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.course_delete",
            user_id=actor_id,
            resource=f"course:{course_id}",
            request=request,
        )
        return {"ok": True}

    async def upsert_course_member(
        self,
        course_id: str,
        body: AdminCourseMemberUpdate,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        course = (await self.db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        user = (await self.db.execute(select(User.id).where(User.id == body.user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        member = (
            await self.db.execute(
                select(CourseMember).where(
                    and_(CourseMember.course_id == course_id, CourseMember.user_id == body.user_id)
                )
            )
        ).scalar_one_or_none()
        role = "instructor" if body.user_id == course.owner_id else body.role
        if member is None:
            self.db.add(CourseMember(course_id=course_id, user_id=body.user_id, role=role))
        else:
            if body.user_id == course.owner_id and body.role != "instructor":
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course owner role is fixed")
            member.role = role
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.course_member_upsert",
            user_id=actor_id,
            resource=f"course:{course_id}:user:{body.user_id}",
            request=request,
            detail={"role": role},
        )
        return await self.course_detail(course_id)

    async def remove_course_member(
        self,
        course_id: str,
        user_id: str,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        course = (await self.db.execute(select(Course).where(Course.id == course_id))).scalar_one_or_none()
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if user_id == course.owner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course owner cannot be removed")
        member = (
            await self.db.execute(
                select(CourseMember).where(
                    and_(CourseMember.course_id == course_id, CourseMember.user_id == user_id)
                )
            )
        ).scalar_one_or_none()
        if member is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course member not found")
        await self.db.delete(member)
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.course_member_remove",
            user_id=actor_id,
            resource=f"course:{course_id}:user:{user_id}",
            request=request,
        )
        return await self.course_detail(course_id)

    async def add_course_document(
        self,
        course_id: str,
        body: CourseDocumentRequest,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        course = (await self.db.execute(select(Course.id).where(Course.id == course_id))).scalar_one_or_none()
        if course is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        doc = (await self.db.execute(select(Document).where(Document.id == body.doc_id))).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        if doc.status != "ready":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Document is not ready")
        owner_member = (
            await self.db.execute(
                select(CourseMember).where(
                    and_(CourseMember.course_id == course_id, CourseMember.user_id == doc.user_id)
                )
            )
        ).scalar_one_or_none()
        if owner_member is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Document owner must be a course member",
            )
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
        await AuditService(self.db).log(
            "admin.course_document_add",
            user_id=actor_id,
            resource=f"course:{course_id}:document:{body.doc_id}",
            request=request,
            detail={"owner_id": doc.user_id, "filename": doc.filename},
        )
        return await self.course_detail(course_id)

    async def remove_course_document(
        self,
        course_id: str,
        doc_id: str,
        actor_id: str | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
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
        await AuditService(self.db).log(
            "admin.course_document_remove",
            user_id=actor_id,
            resource=f"course:{course_id}:document:{doc_id}",
            request=request,
        )
        return await self.course_detail(course_id)

    async def _remove_document_references(self, doc_id: str) -> None:
        sessions = (
            await self.db.execute(select(ChatSession).where(ChatSession.doc_ids.like(f'%"{doc_id}"%')))
        ).scalars().all()
        for session in sessions:
            doc_ids = [item for item in from_json_list(session.doc_ids) if item != doc_id]
            session.doc_ids = to_json(doc_ids)

        messages = (
            await self.db.execute(select(ChatMessage).where(ChatMessage.citations.like(f"%{doc_id}%")))
        ).scalars().all()
        for message in messages:
            citations = from_json_list(message.citations)
            filtered = [
                item
                for item in citations
                if not isinstance(item, dict) or item.get("doc_id") != doc_id
            ]
            if len(filtered) != len(citations):
                message.citations = to_json(filtered)

        quizzes = (
            await self.db.execute(select(Quiz).where(Quiz.doc_ids.like(f'%"{doc_id}"%')))
        ).scalars().all()
        for quiz in quizzes:
            doc_ids = [item for item in from_json_list(quiz.doc_ids) if item != doc_id]
            if doc_ids:
                quiz.doc_ids = to_json(doc_ids)
            else:
                await self.db.delete(quiz)

    async def stats(self) -> dict[str, Any]:
        users = (await self.db.execute(select(func.count(User.id)))).scalar_one()
        documents = (await self.db.execute(select(func.count(Document.id)))).scalar_one()
        tokens = (
            await self.db.execute(select(func.coalesce(func.sum(TokenUsage.tokens_used), 0)))
        ).scalar_one()
        return {"users": users, "documents": documents, "tokens_used": tokens}

    async def get_llm_config(self) -> dict[str, Any]:
        config = await self._load_config()
        return _mask_keys(config)

    async def update_llm_config(self, body: AdminConfigUpdate, actor_id: str | None = None) -> dict[str, Any]:
        current = await self._load_config()
        incoming = body.model_dump(exclude_none=True)
        for key, value in incoming.items():
            current[key] = _merge_config(current.get(key, {}), value)
        row = (
            await self.db.execute(select(AdminConfig).where(AdminConfig.key == "llm_config"))
        ).scalar_one_or_none()
        payload = json.dumps(current, ensure_ascii=False)
        if row is None:
            self.db.add(AdminConfig(key="llm_config", value=payload))
        else:
            row.value = payload
            row.updated_at = now_iso()
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.config_update",
            user_id=actor_id,
            resource="admin_config:llm_config",
            detail=incoming,
        )
        return _mask_keys(current)

    async def cost_stats(self) -> dict[str, Any]:
        return await cost_stats(self.db)

    async def reliability_stats(self) -> dict[str, Any]:
        since = (datetime.now(UTC) - timedelta(days=7)).isoformat()
        rows = (
            await self.db.execute(
                select(SystemEvent)
                .where(and_(SystemEvent.event_type == "llm_fallback", SystemEvent.created_at >= since))
                .order_by(desc(SystemEvent.created_at))
            )
        ).scalars().all()
        by_reason: dict[str, int] = {}
        daily: dict[str, int] = {}
        events = []
        for row in rows:
            detail = json.loads(row.detail)
            reason = detail.get("reason", "unknown")
            by_reason[reason] = by_reason.get(reason, 0) + 1
            day = row.created_at[:10]
            daily[day] = daily.get(day, 0) + 1
            events.append(
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "severity": row.severity,
                    "detail": detail,
                    "created_at": row.created_at,
                }
            )
        return {
            "fallback_count_7d": len(rows),
            "by_reason": by_reason,
            "daily_series": [{"date": key, "count": daily[key]} for key in sorted(daily)],
            "events": events[:50],
        }

    async def audit_logs(
        self,
        user_id: str | None = None,
        action: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await AuditService(self.db).list_logs(user_id, action, from_date, to_date, limit, offset)

    async def deletion_status(self) -> list[dict[str, Any]]:
        users = (
            await self.db.execute(
                select(User)
                .where(User.deletion_requested_at.is_not(None))
                .order_by(desc(User.deletion_requested_at))
            )
        ).scalars().all()
        return [
            {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "deletion_requested_at": user.deletion_requested_at,
                "deletion_scheduled_at": user.deletion_scheduled_at,
            }
            for user in users
        ]

    async def user_deletion_status(self, user_id: str) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "deletion_requested_at": user.deletion_requested_at,
            "deletion_scheduled_at": user.deletion_scheduled_at,
            "export_expires_at": user.export_expires_at,
        }

    async def force_purge_user(self, user_id: str, actor_id: str) -> dict[str, Any]:
        return await PrivacyService(self.db).force_purge(user_id, actor_id=actor_id)

    async def _usage_by_user(self, user_ids: list[str]) -> dict[str, int]:
        if not user_ids:
            return {}
        month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        rows = (
            await self.db.execute(
                select(TokenUsage.user_id, func.coalesce(func.sum(TokenUsage.tokens_used), 0))
                .where(and_(TokenUsage.user_id.in_(user_ids), TokenUsage.created_at >= month_start.isoformat()))
                .group_by(TokenUsage.user_id)
            )
        ).all()
        return {user_id: int(total) for user_id, total in rows}

    async def _document_stats(self, user_ids: list[str]) -> dict[str, dict[str, int]]:
        if not user_ids:
            return {}
        aggregate_rows = (
            await self.db.execute(
                select(
                    Document.user_id,
                    func.count(Document.id),
                    func.coalesce(func.sum(Document.file_size), 0),
                )
                .where(Document.user_id.in_(user_ids))
                .group_by(Document.user_id)
            )
        ).all()
        stats = {
            user_id: {"document_count": int(count), "storage_bytes": int(storage)}
            for user_id, count, storage in aggregate_rows
        }
        status_rows = (
            await self.db.execute(
                select(Document.user_id, Document.status, func.count(Document.id))
                .where(Document.user_id.in_(user_ids))
                .group_by(Document.user_id, Document.status)
            )
        ).all()
        for user_id, status_value, count in status_rows:
            stats.setdefault(user_id, {"document_count": 0, "storage_bytes": 0})
            stats[user_id].setdefault("documents_by_status", {})
            stats[user_id]["documents_by_status"][status_value] = int(count)
        return stats

    def _user_summary(
        self,
        user: User,
        token_used_this_month: int,
        document_stats: dict[str, Any],
    ) -> dict[str, Any]:
        quota_percent = int(token_used_this_month / user.token_quota * 100) if user.token_quota else 100
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "quota_mb": user.quota_mb,
            "token_quota": user.token_quota,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "deletion_requested_at": user.deletion_requested_at,
            "deletion_scheduled_at": user.deletion_scheduled_at,
            "token_used_this_month": token_used_this_month,
            "quota_percent": quota_percent,
            "quota_status": "exceeded" if quota_percent >= 100 else "warning" if quota_percent >= 80 else "ok",
            "document_count": document_stats.get("document_count", 0),
            "storage_bytes": document_stats.get("storage_bytes", 0),
            "documents_by_status": document_stats.get("documents_by_status", {}),
        }

    async def _load_config(self) -> dict[str, Any]:
        default = default_llm_config()
        row = (
            await self.db.execute(select(AdminConfig).where(AdminConfig.key == "llm_config"))
        ).scalar_one_or_none()
        if row is None:
            return default
        saved = json.loads(row.value)
        for key, value in saved.items():
            default.setdefault(key, {}).update(value)
        return default

    async def _ensure_another_active_admin(self, user_id: str) -> None:
        count = (
            await self.db.execute(
                select(func.count(User.id)).where(
                    and_(User.id != user_id, User.role == "admin", User.is_active == 1)
                )
            )
        ).scalar_one()
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot disable or demote the last active admin",
            )


def default_llm_config() -> dict[str, Any]:
    return {
        "chat": {
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "model": settings.LLM_CHAT_MODEL,
            "max_tokens": 4096,
            "temperature": 0.3,
        },
        "vision": {
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "model": settings.LLM_VISION_MODEL,
            "max_tokens": 2048,
        },
        "embedding": {
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "model": settings.LLM_EMBED_MODEL,
            "dimensions": 1536,
        },
        "cost_per_1k_tokens": {
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "text-embedding-3-small": {"input": 0.00002, "output": 0.00002},
        },
        "fallback_providers": {},
    }


def _mask_keys(config: dict[str, Any]) -> dict[str, Any]:
    safe = json.loads(json.dumps(config))
    _mask_in_place(safe)
    return safe


def _mask_in_place(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "api_key" and item:
                value[key] = "********"
            else:
                _mask_in_place(item)
    elif isinstance(value, list):
        for item in value:
            _mask_in_place(item)


def _merge_config(current: Any, incoming: Any) -> Any:
    if isinstance(current, dict) and isinstance(incoming, dict):
        merged = json.loads(json.dumps(current))
        for key, value in incoming.items():
            if key == "api_key" and value == "********":
                continue
            merged[key] = _merge_config(merged.get(key), value)
        return merged
    if incoming == "********":
        return current
    return incoming
