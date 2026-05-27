import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_student
from app.models.session import Session
from app.models.task import Task
from app.models.uploaded_file import UploadedFile as UploadedFileModel
from app.models.generated_file import GeneratedFile
from app.models.progress_event import ProgressEvent
from app.services.task_service import run_task
from app.services.progress_service import get_task_queue, get_events_for_task
from app.utils.validators import validate_file_extension, validate_file_size, validate_mime_type, check_assignment_text
from app.utils.file_utils import get_upload_path

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    assignment_text: str = ""
    output_formats: list[str]
    has_assignment_files: bool = False


class TaskResponse(BaseModel):
    id: str
    status: str
    assignment_text: str
    output_formats: list
    input_summary: str | None
    output_text: str | None
    structured_output_json: dict | None
    error_message: str | None
    created_at: str
    updated_at: str
    uploaded_files: list[dict]
    generated_files: list[dict]
    progress_events: list[dict]

    model_config = {"from_attributes": True}


@router.post("", response_model=dict)
async def create_task(
    req: CreateTaskRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    has_text = bool(req.assignment_text and req.assignment_text.strip())
    if not has_text and not req.has_assignment_files:
        raise HTTPException(status_code=400, detail="請輸入作業敘述或上傳作業檔案（至少擇一）")

    warning_kw = None
    if has_text:
        valid, warning_kw = check_assignment_text(req.assignment_text)
        if not valid:
            raise HTTPException(status_code=400, detail=warning_kw)

    valid_formats = {"txt", "docx", "pdf", "xlsx"}
    formats = [f for f in req.output_formats if f in valid_formats]
    if not formats:
        formats = ["txt"]

    task = Task(
        user_id=session.user_id,
        assignment_text=req.assignment_text,
        output_formats=formats,
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    background_tasks.add_task(run_task, task.id)

    response = {"task_id": task.id, "status": "pending"}
    if warning_kw:
        response["warning"] = f"偵測到可能不當意圖關鍵字「{warning_kw}」，系統將改為提供學習輔助版本。"
    return response


@router.post("/{task_id}/files")
async def upload_file(
    task_id: str,
    file: UploadFile = File(...),
    file_category: str = Form(...),
    session: Session = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == session.user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")

    if file_category not in ("course_material", "assignment_file"):
        raise HTTPException(status_code=400, detail="無效的檔案類別")

    ok, msg = validate_file_extension(file.filename)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    ok, msg = validate_mime_type(file.filename, file.content_type)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    content = await file.read()
    ok, msg = validate_file_size(len(content))
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    ext = Path(file.filename).suffix.lower().lstrip(".")
    stored_path = get_upload_path(task_id, file.filename)
    stored_path.write_bytes(content)

    uploaded = UploadedFileModel(
        task_id=task_id,
        user_id=session.user_id,
        file_category=file_category,
        original_filename=file.filename,
        stored_path=str(stored_path),
        file_type=ext,
        file_size=len(content),
        parse_status="pending",
    )
    db.add(uploaded)
    await db.commit()
    await db.refresh(uploaded)

    return {
        "file_id": uploaded.id,
        "filename": file.filename,
        "size": len(content),
        "category": file_category,
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    session: Session = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")

    if session.role != "admin" and task.user_id != session.user_id:
        raise HTTPException(status_code=403, detail="無權限查看此任務")

    return TaskResponse(
        id=task.id,
        status=task.status,
        assignment_text=task.assignment_text,
        output_formats=task.output_formats,
        input_summary=task.input_summary,
        output_text=task.output_text,
        structured_output_json=task.structured_output_json,
        error_message=task.error_message,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
        uploaded_files=[
            {
                "id": f.id,
                "filename": f.original_filename,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "category": f.file_category,
                "parse_status": f.parse_status,
                "parsed_text_preview": (f.parsed_text[:200] + "...") if f.parsed_text and len(f.parsed_text) > 200 else f.parsed_text,
                "error_message": f.error_message,
            }
            for f in task.uploaded_files
        ],
        generated_files=[
            {
                "id": g.id,
                "format": g.format,
                "status": g.status,
                "error_message": g.error_message,
            }
            for g in task.generated_files
        ],
        progress_events=[
            {
                "id": e.id,
                "event_type": e.event_type,
                "message": e.message,
                "detail": e.detail,
                "created_at": e.created_at.isoformat(),
            }
            for e in task.progress_events
        ],
    )


@router.get("/{task_id}/events")
async def task_events_sse(
    task_id: str,
    session: Session = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    if session.role != "admin" and task.user_id != session.user_id:
        raise HTTPException(status_code=403, detail="無權限")

    async def event_generator():
        # First send existing events
        events = await get_events_for_task(db, task_id)
        for e in events:
            data = json.dumps({
                "event_type": e.event_type,
                "message": e.message,
                "detail": e.detail,
            }, ensure_ascii=False)
            yield f"data: {data}\n\n"

        # Check if task already completed
        result2 = await db.execute(select(Task).where(Task.id == task_id))
        current_task = result2.scalar_one()
        if current_task.status in ("completed", "failed"):
            yield f"data: {json.dumps({'event_type': 'done', 'message': '串流結束'}, ensure_ascii=False)}\n\n"
            return

        # Listen for new events
        queue = get_task_queue(task_id)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=60)
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
                if event.get("event_type") in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                yield f": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{task_id}/download/{file_id}")
async def download_file(
    task_id: str,
    file_id: str,
    session: Session = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    if session.role != "admin" and task.user_id != session.user_id:
        raise HTTPException(status_code=403, detail="無權限下載")

    result = await db.execute(
        select(GeneratedFile).where(GeneratedFile.id == file_id, GeneratedFile.task_id == task_id)
    )
    gen_file = result.scalar_one_or_none()
    if not gen_file:
        raise HTTPException(status_code=404, detail="檔案不存在")
    if gen_file.status != "success":
        raise HTTPException(status_code=400, detail="檔案產生失敗，無法下載")

    file_path = Path(gen_file.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="檔案已過期或不存在")

    media_types = {
        "txt": "text/plain",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    title = "output"
    if task.structured_output_json and task.structured_output_json.get("title"):
        title = task.structured_output_json["title"][:50]

    return FileResponse(
        path=str(file_path),
        media_type=media_types.get(gen_file.format, "application/octet-stream"),
        filename=f"{title}.{gen_file.format}",
    )


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    session: Session = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任務不存在")
    if session.role != "admin" and task.user_id != session.user_id:
        raise HTTPException(status_code=403, detail="無權限刪除")

    await db.delete(task)
    await db.commit()
    return {"success": True}
