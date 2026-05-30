from __future__ import annotations

from pathlib import Path
from typing import Iterable

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Task, UploadedFile
from app.services.file_parser_service import parse_file, safe_jsonable
from app.utils.file_utils import (
    detect_file_type,
    make_task_upload_dir,
    sanitize_filename,
    unique_storage_path,
)


VALID_FILE_CATEGORIES = {"course_material", "assignment_file"}


class FileTooLargeError(Exception):
    """Raised when an upload exceeds the configured max size."""

    def __init__(self, filename: str, size: int, limit_mb: int) -> None:
        super().__init__(f"檔案 {filename} 超過上限 {limit_mb}MB")
        self.filename = filename
        self.size = size
        self.limit_mb = limit_mb


class InvalidCategoryError(ValueError):
    pass


def create_task(db: Session, user_id: str | None, assignment_text: str) -> Task:
    task = Task(
        user_id=user_id,
        assignment_text=(assignment_text or "").strip(),
        status="pending",
    )
    db.add(task)
    db.flush()
    return task


def list_user_tasks(db: Session, user_id: str | None, limit: int = 50) -> list[Task]:
    stmt = (
        select(Task)
        .where(Task.user_id == user_id)
        .order_by(Task.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_task_for_user(db: Session, task_id: str, user_id: str | None, role: str) -> Task | None:
    task = db.get(Task, task_id)
    if task is None:
        return None
    if role == "admin":
        return task
    if task.user_id != user_id:
        return None
    return task


def list_task_files(db: Session, task_id: str) -> list[UploadedFile]:
    stmt = (
        select(UploadedFile)
        .where(UploadedFile.task_id == task_id)
        .order_by(UploadedFile.created_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


async def save_and_parse_uploads(
    db: Session,
    task: Task,
    files: Iterable[UploadFile],
    category: str,
) -> list[UploadedFile]:
    if category not in VALID_FILE_CATEGORIES:
        raise InvalidCategoryError(f"未知檔案分類：{category}")

    settings = get_settings()
    upload_dir = make_task_upload_dir(Path(settings.upload_dir), task.id)
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    out: list[UploadedFile] = []

    for upload in files:
        if upload.filename is None:
            continue

        clean_name = sanitize_filename(upload.filename)
        target_path = unique_storage_path(upload_dir, clean_name)

        size = 0
        chunk_size = 1024 * 1024
        with target_path.open("wb") as fp:
            while True:
                chunk = await upload.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    fp.close()
                    target_path.unlink(missing_ok=True)
                    raise FileTooLargeError(upload.filename, size, settings.max_file_size_mb)
                fp.write(chunk)

        file_type = detect_file_type(clean_name)
        parse_result = parse_file(target_path, file_type)

        uf = UploadedFile(
            task_id=task.id,
            user_id=task.user_id,
            file_category=category,
            original_filename=upload.filename,
            stored_path=str(target_path),
            file_type=file_type,
            file_size=size,
            parse_status=parse_result.parse_status,
            parsed_text=parse_result.parsed_text,
            parsed_table_json=safe_jsonable(parse_result.parsed_table_json),
            summary=parse_result.summary,
            error_message=parse_result.error_message,
        )
        db.add(uf)
        db.flush()
        out.append(uf)

    return out
