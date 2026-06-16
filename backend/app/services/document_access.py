from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Course, CourseDocument, CourseMember, Document


class DocumentAccessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def accessible_document_condition(self, user_id: str):
        shared_docs = (
            select(CourseDocument.doc_id)
            .join(CourseMember, CourseMember.course_id == CourseDocument.course_id)
            .join(Course, Course.id == CourseDocument.course_id)
            .where(
                and_(
                    CourseMember.user_id == user_id,
                    Course.is_active == 1,
                    CourseDocument.is_active == 1,
                )
            )
        )
        return or_(
            and_(Document.user_id == user_id, Document.status != "archived"),
            and_(Document.id.in_(shared_docs), Document.status == "ready"),
        )

    async def list_accessible_documents(self, user_id: str) -> list[Document]:
        shared_docs = (
            select(CourseDocument.doc_id)
            .join(CourseMember, CourseMember.course_id == CourseDocument.course_id)
            .join(Course, Course.id == CourseDocument.course_id)
            .where(
                and_(
                    CourseMember.user_id == user_id,
                    Course.is_active == 1,
                    CourseDocument.is_active == 1,
                )
            )
        )
        rows = (
            await self.db.execute(
                select(Document)
                .where(
                    or_(
                        Document.user_id == user_id,
                        and_(Document.id.in_(shared_docs), Document.status == "ready"),
                    )
                )
                .order_by(desc(Document.created_at))
            )
        ).scalars().all()
        return list(rows)

    async def accessible_doc_ids(self, user_id: str, doc_ids: list[str] | None = None) -> list[str]:
        conditions = [self.accessible_document_condition(user_id)]
        if doc_ids:
            conditions.append(Document.id.in_(doc_ids))
        rows = (
            await self.db.execute(select(Document.id).where(and_(*conditions)))
        ).scalars().all()
        return list(rows)

    async def shared_doc_ids(self, user_id: str, doc_ids: list[str] | None = None) -> list[str]:
        conditions = [
            CourseMember.user_id == user_id,
            Course.is_active == 1,
            CourseDocument.is_active == 1,
        ]
        if doc_ids:
            conditions.append(CourseDocument.doc_id.in_(doc_ids))
        rows = (
            await self.db.execute(
                select(CourseDocument.doc_id)
                .join(CourseMember, CourseMember.course_id == CourseDocument.course_id)
                .join(Course, Course.id == CourseDocument.course_id)
                .where(and_(*conditions))
            )
        ).scalars().all()
        return list(set(rows))
