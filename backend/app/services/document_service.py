import uuid
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.document import Document
from app.utils.file_parsers import parse_file_async, count_tokens

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md", ".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = settings.max_file_size_mb * 1024 * 1024


def _safe_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


async def upload_document(
    db: AsyncSession,
    user_id: int,
    original_filename: str,
    file_bytes: bytes,
    course_name: str | None = None,
    lesson_topic: str | None = None,
    learning_goals: str | None = None,
) -> Document:
    ext = _safe_ext(original_filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支援的檔案格式：{ext}")
    if len(file_bytes) > MAX_BYTES:
        raise ValueError(f"檔案超過 {settings.max_file_size_mb} MB 限制")

    filename = f"{uuid.uuid4().hex}{ext}"
    save_path = settings.uploads_dir / filename
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(file_bytes)

    doc = Document(
        user_id=user_id,
        filename=filename,
        original_filename=original_filename,
        file_type=ext.lstrip("."),
        file_size=len(file_bytes),
        course_name=course_name.strip()[:120] if course_name and course_name.strip() else None,
        lesson_topic=lesson_topic.strip()[:160] if lesson_topic and lesson_topic.strip() else None,
        learning_goals=learning_goals.strip()[:2000] if learning_goals and learning_goals.strip() else None,
        parsed_text=None,
        token_count=0,
        parse_status="uploaded",
        index_status="pending",
        error_message=None,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def process_document(doc_id: int) -> None:
    from app.services.rag_service import index_document

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            return

        try:
            doc.parse_status = "parsing"
            doc.index_status = "pending"
            doc.error_message = None
            await db.commit()

            file_path = settings.uploads_dir / doc.filename
            file_bytes = file_path.read_bytes()
            parsed_text = await parse_file_async(doc.original_filename, file_bytes)
            token_count = count_tokens(parsed_text)

            doc.parsed_text = parsed_text
            doc.token_count = token_count
            doc.parse_status = "ready"
            await db.commit()

            if (
                token_count >= settings.rag_token_threshold
                and parsed_text
                and not settings.demo_mode
                and settings.openai_compatible_api_key
            ):
                try:
                    doc.index_status = "indexing"
                    await db.commit()
                    await index_document(doc.id, doc.user_id, parsed_text)
                    doc.index_status = "indexed"
                except Exception as exc:
                    doc.index_status = "failed"
                    doc.error_message = str(exc)[:2000]
            else:
                doc.index_status = "indexed"
            await db.commit()
        except Exception as exc:
            doc.parse_status = "failed"
            doc.index_status = "failed"
            doc.error_message = str(exc)[:2000]
            await db.commit()


async def list_documents(db: AsyncSession, user_id: int) -> list[Document]:
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    return list(result.scalars().all())


async def get_document(db: AsyncSession, doc_id: int, user_id: int) -> Document | None:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete_document(db: AsyncSession, doc_id: int, user_id: int) -> bool:
    doc = await get_document(db, doc_id, user_id)
    if not doc:
        return False
    file_path = settings.uploads_dir / doc.filename
    if file_path.exists():
        file_path.unlink()
    await db.delete(doc)
    await db.commit()
    return True
