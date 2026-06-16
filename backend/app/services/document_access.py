from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import CourseDocument, CourseMember, Document


class DocumentAccessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def accessible_document_condition(self, user_id: str):
        shared_docs = (
            select(CourseDocument.doc_id)
            .join(CourseMember, CourseMember.course_id == CourseDocument.course_id)
            .where(CourseMember.user_id == user_id)
        )
        return or_(Document.user_id == user_id, Document.id.in_(shared_docs))

    async def list_accessible_documents(self, user_id: str) -> list[Document]:
        rows = (
            await self.db.execute(
                select(Document)
                .where(self.accessible_document_condition(user_id))
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
        conditions = [CourseMember.user_id == user_id]
        if doc_ids:
            conditions.append(CourseDocument.doc_id.in_(doc_ids))
        rows = (
            await self.db.execute(
                select(CourseDocument.doc_id)
                .join(CourseMember, CourseMember.course_id == CourseDocument.course_id)
                .where(and_(*conditions))
            )
        ).scalars().all()
        return list(set(rows))
