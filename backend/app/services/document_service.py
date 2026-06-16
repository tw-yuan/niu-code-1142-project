import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import ChatMessage, ChatSession, Document, Flashcard, Quiz, QuizAttempt
from app.services.chroma_service import ChromaService
from app.services.document_access import DocumentAccessService
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
        if len(processing_count) >= 10:
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
        try:
            local_path, file_size, file_type = await save_upload(user_id, doc.id, upload)
            await ensure_user_quota(self.db, user_id, file_size)
        except Exception:
            await self.db.rollback()
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
        return await DocumentAccessService(self.db).list_accessible_documents(user_id)

    async def get_document(self, user_id: str, doc_id: str) -> Document:
        doc = (
            await self.db.execute(
                select(Document).where(
                    and_(
                        Document.id == doc_id,
                        DocumentAccessService(self.db).accessible_document_condition(user_id),
                    )
                )
            )
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc

    async def get_owned_document(self, user_id: str, doc_id: str) -> Document:
        doc = (
            await self.db.execute(
                select(Document).where(and_(Document.id == doc_id, Document.user_id == user_id))
            )
        ).scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return doc

    async def delete_document(self, user_id: str, doc_id: str) -> None:
        doc = await self.get_owned_document(user_id, doc_id)
        await ChromaService().delete_doc_chunks(user_id, doc_id)
        await self.db.delete(doc)
        await self.db.commit()
        remove_document_dir(user_id, doc_id)

    async def page_path(self, user_id: str, doc_id: str, page_num: int) -> Path:
        doc = await self.get_document(user_id, doc_id)
        path = page_image_path(doc.user_id, doc_id, page_num)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
        return path

    async def content(self, user_id: str, doc_id: str) -> dict[str, Any]:
        doc = await self.get_document(user_id, doc_id)
        pages = await self._content_pages(user_id, doc)
        return {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "status": doc.status,
            "page_count": doc.page_count,
            "pages": pages,
            "content": "\n\n".join(
                f"=== 第 {page['page_num']} 頁 ===\n{page['text']}" for page in pages
            ),
        }

    async def coverage(self, user_id: str, doc_id: str) -> dict[str, list[dict[str, Any]]]:
        doc = await self.get_document(user_id, doc_id)
        shared_doc_ids = await DocumentAccessService(self.db).shared_doc_ids(user_id, [doc_id])
        chunks = await ChromaService().get_document_chunks(user_id, [doc_id], shared_doc_ids)
        pages = sorted(
            {
                int(item["metadata"].get("page_num", 1))
                for item in chunks
                if item["metadata"].get("page_num")
            }
        )
        if not pages and doc.page_count:
            pages = list(range(1, doc.page_count + 1))
        if not pages:
            return {"chapters": []}

        chapter_size = 10
        chapters = []
        for start in range(min(pages), max(pages) + 1, chapter_size):
            end = min(start + chapter_size - 1, max(pages))
            chapters.append(
                {
                    "title": f"第 {len(chapters) + 1} 區段",
                    "page_range": [start, end],
                    "quiz_attempts": 0,
                    "quiz_score_avg": 0.0,
                    "flashcard_count": 0,
                    "flashcard_mastered": 0,
                    "chat_mentions": 0,
                    "coverage_score": 0.0,
                }
            )

        flashcards = (
            await self.db.execute(
                select(Flashcard).where(and_(Flashcard.user_id == user_id, Flashcard.doc_id == doc_id))
            )
        ).scalars().all()
        for card in flashcards:
            chapter = _chapter_for_page(chapters, card.source_page)
            if chapter is None:
                continue
            chapter["flashcard_count"] += 1
            if card.repetition >= 2:
                chapter["flashcard_mastered"] += 1

        scores = await self._quiz_scores_for_doc(user_id, doc_id)
        for chapter in chapters:
            chapter["quiz_attempts"] = len(scores)
            chapter["quiz_score_avg"] = round(sum(scores) / len(scores), 4) if scores else 0.0

        mentions = await self._chat_mentions(user_id, doc_id)
        for page, count in mentions.items():
            chapter = _chapter_for_page(chapters, page)
            if chapter is not None:
                chapter["chat_mentions"] += count

        for chapter in chapters:
            flashcard_score = (
                chapter["flashcard_mastered"] / chapter["flashcard_count"]
                if chapter["flashcard_count"]
                else 0.0
            )
            chapter["coverage_score"] = round(
                chapter["quiz_score_avg"] * 0.4
                + flashcard_score * 0.4
                + min(chapter["chat_mentions"] / 3, 1.0) * 0.2,
                4,
            )
        return {"chapters": chapters}

    async def _quiz_scores_for_doc(self, user_id: str, doc_id: str) -> list[float]:
        quizzes = (
            await self.db.execute(select(Quiz).where(Quiz.user_id == user_id))
        ).scalars().all()
        quiz_ids = [quiz.id for quiz in quizzes if doc_id in json.loads(quiz.doc_ids)]
        if not quiz_ids:
            return []
        attempts = (
            await self.db.execute(
                select(QuizAttempt).where(
                    and_(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id.in_(quiz_ids))
                )
            )
        ).scalars().all()
        return [float(attempt.total_score or 0) for attempt in attempts]

    async def _chat_mentions(self, user_id: str, doc_id: str) -> dict[int, int]:
        sessions = (
            await self.db.execute(select(ChatSession.id).where(ChatSession.user_id == user_id))
        ).scalars().all()
        if not sessions:
            return {}
        messages = (
            await self.db.execute(
                select(ChatMessage).where(
                    and_(ChatMessage.session_id.in_(sessions), ChatMessage.citations != "[]")
                )
            )
        ).scalars().all()
        mentions: dict[int, int] = {}
        for message in messages:
            for citation in json.loads(message.citations):
                if citation.get("doc_id") == doc_id and citation.get("page"):
                    page = int(citation["page"])
                    mentions[page] = mentions.get(page, 0) + 1
        return mentions

    async def _content_pages(self, user_id: str, doc: Document) -> list[dict[str, Any]]:
        if doc.file_type == "md":
            path = Path(doc.local_path)
            if path.exists():
                text = await _read_text(path)
                return [{"page_num": 1, "text": text}]

        cached_pages = await _ocr_cache_pages(Path(doc.local_path).parent / "pages" / "ocr_cache.json")
        if cached_pages:
            return cached_pages

        shared_doc_ids = await DocumentAccessService(self.db).shared_doc_ids(user_id, [doc.id])
        chunks = await ChromaService().get_document_chunks(user_id, [doc.id], shared_doc_ids)
        grouped: dict[int, list[str]] = {}
        for chunk in chunks:
            page_num = int(chunk["metadata"].get("page_num") or 1)
            grouped.setdefault(page_num, []).append(str(chunk["text"]))
        return [
            {"page_num": page_num, "text": "\n\n".join(texts)}
            for page_num, texts in sorted(grouped.items())
        ]


def _chapter_for_page(chapters: list[dict[str, Any]], page: int | None) -> dict[str, Any] | None:
    if page is None:
        return chapters[0] if chapters else None
    for chapter in chapters:
        start, end = chapter["page_range"]
        if start <= page <= end:
            return chapter
    return None


async def _read_text(path: Path) -> str:
    import asyncio

    return await asyncio.to_thread(path.read_text, encoding="utf-8", errors="ignore")


async def _ocr_cache_pages(path: Path) -> list[dict[str, Any]]:
    import asyncio

    if not path.exists():
        return []

    def load() -> list[dict[str, Any]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        pages = []
        for raw_page, payload in data.items():
            if not isinstance(payload, dict):
                continue
            try:
                page_num = int(raw_page)
            except ValueError:
                continue
            pages.append({"page_num": page_num, "text": str(payload.get("text") or "")})
        return sorted(pages, key=lambda item: item["page_num"])

    return await asyncio.to_thread(load)
