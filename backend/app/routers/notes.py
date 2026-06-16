from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import NoteCreate, NoteUpdate
from app.services.audit_service import AuditService
from app.services.notes_service import NotesService

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("")
async def create_note(
    body: NoteCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await NotesService(db).create(current_user.id, body)
    await AuditService(db).log(
        "note.create",
        user_id=current_user.id,
        resource=f"note:{note['id']}",
        request=request,
        detail={"doc_id": body.doc_id, "session_id": body.session_id, "source_type": body.source_type},
    )
    return note


@router.get("")
async def list_notes(
    doc_id: str | None = None,
    session_id: str | None = None,
    q: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await NotesService(db).list(current_user.id, doc_id, session_id, q)


@router.put("/{note_id}")
async def update_note(
    note_id: str,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await NotesService(db).update(current_user.id, note_id, body)


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await NotesService(db).delete(current_user.id, note_id)
    return {"ok": True}


@router.get("/export/{doc_id}")
async def export_notes(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await NotesService(db).export_markdown(current_user.id, doc_id)
    return PlainTextResponse(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="learnai-notes-{doc_id}.md"'},
    )
