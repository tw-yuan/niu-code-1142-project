import asyncio
from pathlib import Path

from sqlalchemy import and_, select

from app.models.database import SessionLocal
from app.models.tables import Document, now_iso
from app.services import converter, ocr_service
from app.services.chroma_service import ChromaService
from app.services.chunker import chunk_text
from app.services.llm_client import LLMClient
from app.services.ws_manager import push_to_user
from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document(self, doc_id: str, user_id: str):
    try:
        asyncio.run(_process_async(doc_id, user_id))
    except Exception as exc:
        asyncio.run(_set_error(doc_id, user_id, str(exc)))
        raise self.retry(exc=exc) from exc


async def _process_async(doc_id: str, user_id: str) -> None:
    async with SessionLocal() as db:
        doc = (
            await db.execute(
                select(Document).where(and_(Document.id == doc_id, Document.user_id == user_id))
            )
        ).scalar_one_or_none()
        if doc is None:
            return

        original_path = Path(doc.local_path)
        pages_dir = original_path.parent / "pages"
        cache_path = pages_dir / "ocr_cache.json"

        if doc.file_type == "md":
            await _update_status(db, doc, "embedding")
            await push_to_user(user_id, {"type": "doc_status", "doc_id": doc_id, "status": "embedding"})
            raw_text = original_path.read_text(encoding="utf-8", errors="ignore")
            full_text = f"=== 第 1 頁 ===\n{raw_text}"
            page_count = 1
        else:
            await _update_status(db, doc, "converting")
            await push_to_user(user_id, {"type": "doc_status", "doc_id": doc_id, "status": "converting"})
            image_paths = await converter.convert_to_images(str(original_path), str(pages_dir))
            page_count = len(image_paths)

            await _update_status(db, doc, "ocr_processing")

            async def on_progress(current: int, total: int) -> None:
                pct = int(current / total * 100) if total else 100
                await push_to_user(
                    user_id,
                    {
                        "type": "doc_status",
                        "doc_id": doc_id,
                        "status": "ocr_processing",
                        "progress": pct,
                    },
                )

            full_text = await ocr_service.ocr_document(
                image_paths, str(cache_path), user_id, on_progress, db=db
            )

            await _update_status(db, doc, "embedding")
            await push_to_user(user_id, {"type": "doc_status", "doc_id": doc_id, "status": "embedding"})

        chunks = chunk_text(full_text)
        if chunks:
            llm = LLMClient(db)
            embeddings = await llm.embed([c["text"] for c in chunks], user_id=user_id)
            await ChromaService().upsert_chunks(user_id, doc_id, doc.filename, chunks, embeddings)

        doc.status = "ready"
        doc.page_count = page_count
        doc.chunk_count = len(chunks)
        doc.error_msg = None
        doc.updated_at = now_iso()
        await db.commit()
        await push_to_user(user_id, {"type": "doc_ready", "doc_id": doc_id})


async def _update_status(db, doc: Document, status: str) -> None:
    doc.status = status
    doc.updated_at = now_iso()
    await db.commit()


async def _set_error(doc_id: str, user_id: str, message: str) -> None:
    async with SessionLocal() as db:
        doc = (
            await db.execute(
                select(Document).where(and_(Document.id == doc_id, Document.user_id == user_id))
            )
        ).scalar_one_or_none()
        if doc is None:
            return
        doc.status = "error"
        doc.error_msg = message[:2000]
        doc.updated_at = now_iso()
        await db.commit()
        await push_to_user(
            user_id,
            {"type": "doc_status", "doc_id": doc_id, "status": "error", "error": doc.error_msg},
        )
