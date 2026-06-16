from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, rate_limit
from app.models.tables import User
from app.schemas import DocumentContentOut, DocumentOut, DocumentUploadResult
from app.services.audit_service import AuditService
from app.services.document_service import DocumentService
from app.services.legal_service import LegalService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut, dependencies=[rate_limit("documents_upload", 10, 3600)])
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await LegalService(db).require_consent(current_user.id, "copyright_declaration")
    doc = await DocumentService(db).upload(current_user.id, file)
    await AuditService(db).log(
        "document.upload",
        user_id=current_user.id,
        resource=f"document:{doc.id}",
        request=request,
        detail={"filename": doc.filename, "file_size": doc.file_size, "file_type": doc.file_type},
    )
    return doc


@router.post(
    "/upload-batch",
    response_model=list[DocumentUploadResult],
    dependencies=[rate_limit("documents_upload_batch", 5, 3600)],
)
async def upload_documents(
    request: Request,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files uploaded")
    if len(files) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Too many files")

    await LegalService(db).require_consent(current_user.id, "copyright_declaration")
    svc = DocumentService(db)
    audit = AuditService(db)
    results: list[dict] = []
    for upload in files:
        filename = upload.filename or "upload"
        try:
            doc = await svc.upload(current_user.id, upload)
            await audit.log(
                "document.upload",
                user_id=current_user.id,
                resource=f"document:{doc.id}",
                request=request,
                detail={
                    "filename": doc.filename,
                    "file_size": doc.file_size,
                    "file_type": doc.file_type,
                },
            )
            results.append({"filename": doc.filename, "ok": True, "document": doc})
        except HTTPException as exc:
            await db.rollback()
            results.append({"filename": filename, "ok": False, "error": _error_detail(exc.detail)})
        except Exception as exc:
            await db.rollback()
            results.append({"filename": filename, "ok": False, "error": str(exc)})
    return results


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
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await DocumentService(db).delete_document(current_user.id, doc_id)
    await AuditService(db).log(
        "document.delete",
        user_id=current_user.id,
        resource=f"document:{doc_id}",
        request=request,
    )
    return {"ok": True}


@router.get("/{doc_id}/status", response_model=DocumentOut)
async def get_status(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).get_document(current_user.id, doc_id)


@router.get("/{doc_id}/coverage")
async def get_coverage(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).coverage(current_user.id, doc_id)


@router.get("/{doc_id}/content", response_model=DocumentContentOut)
async def get_content(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await DocumentService(db).content(current_user.id, doc_id)


@router.get("/{doc_id}/pages/{page_num}")
async def get_page_image(
    doc_id: str,
    page_num: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    path = await DocumentService(db).page_path(current_user.id, doc_id, page_num)
    await AuditService(db).log(
        "document.download",
        user_id=current_user.id,
        resource=f"document:{doc_id}:page:{page_num}",
        request=request,
    )
    return FileResponse(path, media_type="image/png")


def _error_detail(detail: object) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("detail") or detail.get("code")
        if isinstance(message, str):
            return message
    return "Upload failed"
