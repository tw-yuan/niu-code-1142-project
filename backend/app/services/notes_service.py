from fastapi import HTTPException, status
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import ChatSession, Document, Note, now_iso
from app.schemas import NoteCreate, NoteUpdate
from app.services.document_access import DocumentAccessService


class NotesService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str, body: NoteCreate) -> dict:
        await self._validate_refs(user_id, body.doc_id, body.session_id)
        existing = await self._existing_generated_note(user_id, body)
        if existing:
            return self._out(existing)
        note = Note(
            user_id=user_id,
            doc_id=body.doc_id,
            session_id=body.session_id,
            content=body.content,
            source_page=body.source_page,
            source_type=body.source_type,
        )
        self.db.add(note)
        await self.db.commit()
        await self.db.refresh(note)
        return self._out(note)

    async def _existing_generated_note(self, user_id: str, body: NoteCreate) -> Note | None:
        if body.source_type not in {"flashcard", "quiz", "chat", "summary"}:
            return None
        return (
            await self.db.execute(
                select(Note)
                .where(
                    and_(
                        Note.user_id == user_id,
                        Note.source_type == body.source_type,
                        Note.doc_id.is_(None)
                        if body.doc_id is None
                        else Note.doc_id == body.doc_id,
                        Note.session_id.is_(None)
                        if body.session_id is None
                        else Note.session_id == body.session_id,
                        Note.source_page.is_(None)
                        if body.source_page is None
                        else Note.source_page == body.source_page,
                        Note.content == body.content,
                    )
                )
                .order_by(desc(Note.updated_at))
            )
        ).scalars().first()

    async def list(
        self,
        user_id: str,
        doc_id: str | None = None,
        session_id: str | None = None,
        q: str | None = None,
    ) -> list[dict]:
        conditions = [Note.user_id == user_id]
        if doc_id:
            conditions.append(Note.doc_id == doc_id)
        if session_id:
            conditions.append(Note.session_id == session_id)
        if q:
            conditions.append(Note.content.ilike(f"%{q}%"))
        rows = (
            await self.db.execute(
                select(Note).where(and_(*conditions)).order_by(desc(Note.updated_at))
            )
        ).scalars().all()
        return [self._out(row) for row in rows]

    async def update(self, user_id: str, note_id: str, body: NoteUpdate) -> dict:
        note = await self._get(user_id, note_id)
        note.content = body.content
        note.updated_at = now_iso()
        await self.db.commit()
        return self._out(note)

    async def delete(self, user_id: str, note_id: str) -> None:
        note = await self._get(user_id, note_id)
        await self.db.delete(note)
        await self.db.commit()

    async def export_markdown(self, user_id: str, doc_id: str) -> str:
        await self._validate_doc(user_id, doc_id)
        notes = await self.list(user_id, doc_id=doc_id)
        lines = ["# LearnAI 筆記匯出", ""]
        for note in notes:
            source = []
            if note.get("source_page"):
                source.append(f"第 {note['source_page']} 頁")
            if note.get("source_type"):
                source.append(note["source_type"])
            lines.extend(
                [
                    f"## {note['created_at']}",
                    f"> 來源：{', '.join(source) if source else '手動筆記'}",
                    "",
                    note["content"],
                    "",
                ]
            )
        return "\n".join(lines)

    async def _get(self, user_id: str, note_id: str) -> Note:
        note = (
            await self.db.execute(
                select(Note).where(and_(Note.id == note_id, Note.user_id == user_id))
            )
        ).scalar_one_or_none()
        if note is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
        return note

    async def _validate_refs(
        self,
        user_id: str,
        doc_id: str | None,
        session_id: str | None,
    ) -> None:
        if doc_id:
            await self._validate_doc(user_id, doc_id)
        if session_id:
            session = (
                await self.db.execute(
                    select(ChatSession).where(
                        and_(ChatSession.id == session_id, ChatSession.user_id == user_id)
                    )
                )
            ).scalar_one_or_none()
            if session is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

    async def _validate_doc(self, user_id: str, doc_id: str) -> None:
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

    def _out(self, note: Note) -> dict:
        return {
            "id": note.id,
            "user_id": note.user_id,
            "doc_id": note.doc_id,
            "session_id": note.session_id,
            "content": note.content,
            "source_page": note.source_page,
            "source_type": note.source_type,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
        }
