from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import DocumentOut
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).upload(current_user.id, file)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).list_documents(current_user.id)


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).get_document(current_user.id, doc_id)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await DocumentService(db).delete_document(current_user.id, doc_id)
    return {"ok": True}


@router.get("/{doc_id}/status", response_model=DocumentOut)
async def get_status(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).get_document(current_user.id, doc_id)


@router.get("/{doc_id}/pages/{page_num}")
async def get_page_image(
    doc_id: str,
    page_num: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    path = await DocumentService(db).page_path(current_user.id, doc_id, page_num)
    return FileResponse(path, media_type="image/png")

