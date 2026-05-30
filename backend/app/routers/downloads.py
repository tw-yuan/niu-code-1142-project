from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_session
from app.models import GeneratedFile
from app.services.auth_service import AuthResult
from app.services.task_service import get_task_for_user

router = APIRouter(prefix="/api/tasks", tags=["tasks-downloads"])


MEDIA_TYPES = {
    "txt": "text/plain; charset=utf-8",
    "md": "text/markdown; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


@router.get("/{task_id}/download/{file_id}")
def download_generated_file(
    task_id: str,
    file_id: str,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
):
    task = get_task_for_user(db, task_id, auth.user_id, auth.role)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到任務")

    gf = db.get(GeneratedFile, file_id)
    if gf is None or gf.task_id != task.id:
        raise HTTPException(status_code=404, detail="找不到檔案")

    settings = get_settings()
    expected_root = Path(settings.generated_file_dir).resolve()
    path = Path(gf.file_path).resolve()
    try:
        path.relative_to(expected_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="檔案路徑不在允許範圍") from exc

    if not path.exists():
        raise HTTPException(status_code=404, detail="檔案不存在或已被刪除")

    media_type = MEDIA_TYPES.get(gf.format.lower(), "application/octet-stream")
    return FileResponse(
        str(path),
        media_type=media_type,
        filename=gf.filename,
    )
