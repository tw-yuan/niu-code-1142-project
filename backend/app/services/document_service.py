import shutil
import uuid
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.document import Document
from app.utils.file_parsers import parse_file_async, count_tokens

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_BYTES = settings.max_file_size_mb * 1024 * 1024


def _safe_ext(filename: str) -> str:
    return Path(filename).suffix.lower()


async def upload_document(
    db: AsyncSession,
    user_id: int,
    original_filename: str,
    file_bytes: bytes,
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

    parsed_text = await parse_file_async(original_filename, file_bytes)
    token_count = count_tokens(parsed_text)

    doc = Document(
        user_id=user_id,
        filename=filename,
        original_filename=original_filename,
        file_type=ext.lstrip("."),
        file_size=len(file_bytes),
        parsed_text=parsed_text,
        token_count=token_count,
        index_status="pending",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


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
