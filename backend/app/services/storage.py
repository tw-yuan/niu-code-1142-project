import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import Document, User

ALLOWED_EXTENSIONS = {".pdf", ".md", ".pptx", ".docx"}
ALLOWED_MIME_PREFIXES = {
    "application/pdf",
    "text/markdown",
    "text/plain",
    "application/vnd.openxmlformats-officedocument",
}


def safe_join(base: Path, *parts: str) -> Path:
    target = (base.joinpath(*parts)).resolve()
    base_resolved = base.resolve()
    if not target.is_relative_to(base_resolved):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid path")
    return target


def extension_for(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")
    return ext


async def ensure_user_quota(db: AsyncSession, user_id: str, incoming_size: int) -> None:
    used = (
        await db.execute(select(func.coalesce(func.sum(Document.file_size), 0)).where(Document.user_id == user_id))
    ).scalar_one()
    quota_mb = (
        await db.execute(select(User.quota_mb).where(User.id == user_id))
    ).scalar_one_or_none() or settings.DEFAULT_USER_QUOTA_MB
    quota = quota_mb * 1024 * 1024
    if used + incoming_size > quota:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Quota exceeded")


async def save_upload(user_id: str, doc_id: str, upload: UploadFile) -> tuple[str, int, str]:
    filename = Path(upload.filename or "upload").name
    ext = extension_for(filename)
    content_type = upload.content_type or ""
    if content_type and not any(
        content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported MIME type")
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    doc_dir = safe_join(settings.upload_path, user_id, doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    target = safe_join(doc_dir, f"original{ext}")

    size = 0
    with target.open("wb") as out:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                target.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File too large",
                )
            out.write(chunk)
    return str(target), size, ext.lstrip(".")


def remove_document_dir(user_id: str, doc_id: str) -> None:
    doc_dir = safe_join(settings.upload_path, user_id, doc_id)
    if doc_dir.exists():
        shutil.rmtree(doc_dir)


def page_image_path(user_id: str, doc_id: str, page_num: int) -> Path:
    if page_num < 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found")
    return safe_join(settings.upload_path, user_id, doc_id, "pages", f"page_{page_num:03d}.png")
