import hashlib
import json
import secrets
import shutil
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import (
    ChatMessage,
    ChatSession,
    Course,
    Document,
    Flashcard,
    Note,
    Quiz,
    QuizAttempt,
    User,
    now_iso,
)
from app.services.audit_service import AuditService
from app.services.chroma_service import ChromaService


class PrivacyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_delete(self, user_id: str) -> dict[str, Any]:
        user = await self._get_user(user_id)
        code = f"{secrets.randbelow(1_000_000):06d}"
        now = datetime.now(UTC)
        user.deletion_requested_at = now.isoformat()
        user.deletion_confirm_code = code
        user.deletion_scheduled_at = (now + timedelta(days=30)).isoformat()
        await self.db.commit()
        await AuditService(self.db).log("data.delete_request", user_id=user_id, resource=f"user:{user_id}")
        return {
            "confirmation_code": code,
            "deletion_requested_at": user.deletion_requested_at,
            "deletion_scheduled_at": user.deletion_scheduled_at,
        }

    async def confirm_delete(self, user_id: str, confirmation_code: str) -> dict[str, Any]:
        user = await self._get_user(user_id)
        if not user.deletion_confirm_code or user.deletion_confirm_code != confirmation_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid confirmation code")
        user.is_active = 0
        await self.db.commit()
        await AuditService(self.db).log("data.delete_confirm", user_id=user_id, resource=f"user:{user_id}")
        return {"ok": True, "deletion_scheduled_at": user.deletion_scheduled_at}

    async def cancel_delete(self, user_id: str) -> dict[str, Any]:
        user = await self._get_user(user_id)
        user.deletion_requested_at = None
        user.deletion_confirm_code = None
        user.deletion_scheduled_at = None
        user.is_active = 1
        await self.db.commit()
        await AuditService(self.db).log("data.delete_cancel", user_id=user_id, resource=f"user:{user_id}")
        return {"ok": True}

    async def export_request(self, user_id: str) -> dict[str, Any]:
        user = await self._get_user(user_id)
        export_dir = settings.data_path / "exports" / user_id
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / "learnai-export.zip"
        payload = await self._export_payload(user)
        with zipfile.ZipFile(export_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for filename, data in payload.items():
                zf.writestr(filename, json.dumps(data, ensure_ascii=False, indent=2))
        user.export_path = str(export_path)
        user.export_expires_at = (datetime.now(UTC) + timedelta(hours=24)).isoformat()
        await self.db.commit()
        await AuditService(self.db).log("data.export", user_id=user_id, resource=f"user:{user_id}")
        return {"ok": True, "expires_at": user.export_expires_at}

    async def export_download_path(self, user_id: str) -> Path:
        user = await self._get_user(user_id)
        if not user.export_path or not user.export_expires_at:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
        if datetime.fromisoformat(user.export_expires_at) < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Export expired")
        path = Path(user.export_path)
        if not path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")
        return path

    async def force_purge(self, user_id: str, actor_id: str | None = None) -> dict[str, Any]:
        user = await self._get_user(user_id)
        username_hash = hashlib.sha256(user.id.encode("utf-8")).hexdigest()[:16]
        await ChromaService().delete_user_chunks(user.id)
        shutil.rmtree(settings.upload_path / user.id, ignore_errors=True)
        shutil.rmtree(settings.data_path / "exports" / user.id, ignore_errors=True)
        await self.db.execute(delete(Course).where(Course.owner_id == user.id))
        await self.db.execute(delete(User).where(User.id == user.id))
        await AuditService(self.db).log(
            "data.purge_complete",
            user_id=actor_id,
            resource=f"user_hash:{username_hash}",
            detail={"purged_user_id_hash": username_hash},
        )
        return {"ok": True}

    async def purge_due_users(self) -> int:
        now = now_iso()
        users = (
            await self.db.execute(
                select(User).where(
                    and_(
                        User.deletion_scheduled_at.is_not(None),
                        User.deletion_scheduled_at <= now,
                    )
                )
            )
        ).scalars().all()
        count = 0
        for user in users:
            await self.force_purge(user.id)
            count += 1
        return count

    async def _export_payload(self, user: User) -> dict[str, Any]:
        documents = (
            await self.db.execute(select(Document).where(Document.user_id == user.id))
        ).scalars().all()
        sessions = (
            await self.db.execute(select(ChatSession).where(ChatSession.user_id == user.id))
        ).scalars().all()
        session_ids = [session.id for session in sessions]
        messages = []
        if session_ids:
            messages = (
                await self.db.execute(
                    select(ChatMessage).where(ChatMessage.session_id.in_(session_ids))
                )
            ).scalars().all()
        flashcards = (
            await self.db.execute(select(Flashcard).where(Flashcard.user_id == user.id))
        ).scalars().all()
        quizzes = (
            await self.db.execute(select(Quiz).where(Quiz.user_id == user.id))
        ).scalars().all()
        attempts = (
            await self.db.execute(select(QuizAttempt).where(QuizAttempt.user_id == user.id))
        ).scalars().all()
        notes = (
            await self.db.execute(select(Note).where(Note.user_id == user.id))
        ).scalars().all()
        return {
            "profile.json": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at,
            },
            "documents.json": [_row_dict(doc, exclude={"local_path"}) for doc in documents],
            "chat_history.json": {
                "sessions": [_row_dict(session) for session in sessions],
                "messages": [_row_dict(message) for message in messages],
            },
            "flashcards.json": [_row_dict(card) for card in flashcards],
            "quizzes.json": [_row_dict(quiz) for quiz in quizzes],
            "quiz_attempts.json": [_row_dict(attempt) for attempt in attempts],
            "notes.json": [_row_dict(note) for note in notes],
        }

    async def _get_user(self, user_id: str) -> User:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user


def _row_dict(row: Any, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    return {
        column.name: getattr(row, column.name)
        for column in row.__table__.columns
        if column.name not in exclude
    }
