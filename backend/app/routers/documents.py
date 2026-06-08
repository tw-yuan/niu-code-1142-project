import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Annotated
from datetime import datetime

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.document import Document
from app.services.document_service import (
    upload_document, list_documents, get_document, delete_document
)
from app.services.direction_service import get_directions
from app.services.rag_service import index_document

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    original_filename: str
    file_type: str
    file_size: int
    token_count: int
    index_status: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("/upload", response_model=DocumentResponse)
async def upload(
    file: Annotated[UploadFile, File()],
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    file_bytes = await file.read()
    try:
        doc = await upload_document(db, user.id, file.filename or "upload", file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if doc.token_count >= 12000 and doc.parsed_text:
        try:
            await index_document(doc.id, doc.parsed_text)
            doc.index_status = "indexed"
            await db.commit()
        except Exception:
            doc.index_status = "failed"
            await db.commit()
    else:
        doc.index_status = "indexed"
        await db.commit()

    return doc


@router.get("", response_model=list[DocumentResponse])
async def list_docs(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    return await list_documents(db, user.id)


@router.get("/{doc_id}", response_model=DocumentResponse)
async def get_doc(
    doc_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    doc = await get_document(db, doc_id, user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    return doc


@router.delete("/{doc_id}")
async def delete_doc(
    doc_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    from app.services.rag_service import delete_document_index
    doc = await get_document(db, doc_id, user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    delete_document_index(doc_id)
    await delete_document(db, doc_id, user.id)
    return {"message": "ok"}


@router.get("/{doc_id}/directions")
async def doc_directions(
    doc_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    refresh: Annotated[bool, Query()] = False,
):
    doc = await get_document(db, doc_id, user.id)
    if not doc:
        raise HTTPException(status_code=404, detail="文件不存在")
    if not doc.parsed_text:
        raise HTTPException(status_code=400, detail="文件尚未解析完成")

    # 有快取且不強制重新生成 → 直接回傳
    if doc.directions_cache and not refresh:
        return {"directions": json.loads(doc.directions_cache), "cached": True}

    # 重新生成並存入快取
    directions = await get_directions(doc.parsed_text)
    doc.directions_cache = json.dumps(directions, ensure_ascii=False)
    await db.commit()
    return {"directions": directions, "cached": False}
