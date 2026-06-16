from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Document
from app.services.chroma_service import ChromaService
from app.services.storage import (
    ensure_user_quota,
    page_image_path,
    remove_document_dir,
    save_upload,
)
from app.tasks.document_tasks import process_document


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def upload(self, user_id: str, upload: UploadFile) -> Document:
        processing_count = (
            await self.db.execute(
                select(Document).where(
                    and_(
                        Document.user_id == user_id,
                        Document.status.in_(["uploading", "converting", "ocr_processing", "embedding"]),
                    )
                )
            )
        ).scalars().all()
        if len(processing_count) >= 3:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many documents are processing",
            )

        doc = Document(
            user_id=user_id,
            filename=Path(upload.filename or "upload").name,
            file_type="pending",
            file_size=0,
            local_path="",
        )
        self.db.add(doc)
        await self.db.flush()
        local_path, file_size, file_type = await save_upload(user_id, doc.id, upload)
        try:
            await ensure_user_quota(self.db, user_id, file_size)
        except Exception:
            remove_document_dir(user_id, doc.id)
            raise
        doc.local_path = local_path
        doc.file_size = file_size
        doc.file_type = file_type
        await self.db.commit()
        await self.db.refresh(doc)
        process_document.apply_async(args=[doc.id, user_id], countdown=0)
        return doc

    async def list_documents(self, user_id: str) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(desc(Document.created_at))
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_document(self, user_id: str, doc_id: str) -> Document:
        doc = (
            await self.db.execute(
                select(Document).where(and_(Document.id == doc_id, Document.user_id == user_id))
            )
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc

    async def delete_document(self, user_id: str, doc_id: str) -> None:
        doc = await self.get_document(user_id, doc_id)
        await ChromaService().delete_doc_chunks(user_id, doc_id)
        await self.db.delete(doc)
        await self.db.commit()
        remove_document_dir(user_id, doc_id)

    async def page_path(self, user_id: str, doc_id: str, page_num: int) -> Path:
        await self.get_document(user_id, doc_id)
        path = page_image_path(user_id, doc_id, page_num)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
        return path
