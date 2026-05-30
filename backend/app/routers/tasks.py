from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_session
from app.models import (
    AgentToolCall,
    GeneratedFile,
    Limitation,
    Reference,
)
from app.services.agent_runtime import run_task_blocking
from app.services.auth_service import AuthResult
from app.services.task_service import (
    FileTooLargeError,
    InvalidCategoryError,
    create_task,
    delete_task,
    get_task_for_user,
    list_task_files,
    list_user_tasks,
    reset_task_for_rerun,
    save_and_parse_uploads,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskBody(BaseModel):
    assignment_text: str = Field(default="", max_length=20_000)


class FileInfo(BaseModel):
    id: str
    file_category: str
    original_filename: str
    file_type: str
    file_size: int
    parse_status: str
    summary: str | None
    error_message: str | None
    created_at: datetime


class ReferenceInfo(BaseModel):
    id: str
    source_name: str
    quote_or_summary: str | None
    used_for: str | None
    created_at: datetime


class LimitationInfo(BaseModel):
    id: str
    text: str
    created_at: datetime


class GeneratedFileInfo(BaseModel):
    id: str
    tool_call_id: str | None
    format: str
    filename: str
    purpose: str | None
    size_bytes: int
    status: str
    created_at: datetime


class TaskInfo(BaseModel):
    id: str
    status: str
    assignment_text: str
    agent_title: str | None
    agent_assignment_summary: str | None
    agent_explanation: str | None
    iterations_used: int
    model_name: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    files: list[FileInfo]
    references: list[ReferenceInfo]
    limitations: list[LimitationInfo]
    generated_files: list[GeneratedFileInfo]


def _file_info(f) -> FileInfo:
    return FileInfo(
        id=f.id,
        file_category=f.file_category,
        original_filename=f.original_filename,
        file_type=f.file_type,
        file_size=f.file_size,
        parse_status=f.parse_status,
        summary=f.summary,
        error_message=f.error_message,
        created_at=f.created_at,
    )


def _load_task_extras(db: Session, task_id: str) -> dict[str, list[Any]]:
    refs = list(
        db.execute(
            select(Reference)
            .where(Reference.task_id == task_id)
            .order_by(Reference.created_at.asc())
        )
        .scalars()
        .all()
    )
    lims = list(
        db.execute(
            select(Limitation)
            .where(Limitation.task_id == task_id)
            .order_by(Limitation.created_at.asc())
        )
        .scalars()
        .all()
    )
    gens = list(
        db.execute(
            select(GeneratedFile)
            .where(GeneratedFile.task_id == task_id)
            .order_by(GeneratedFile.created_at.asc())
        )
        .scalars()
        .all()
    )
    return {"refs": refs, "lims": lims, "gens": gens}


def _task_to_info(task, files, extras: dict[str, list[Any]] | None = None) -> TaskInfo:
    extras = extras or {"refs": [], "lims": [], "gens": []}
    return TaskInfo(
        id=task.id,
        status=task.status,
        assignment_text=task.assignment_text,
        agent_title=task.agent_title,
        agent_assignment_summary=task.agent_assignment_summary,
        agent_explanation=task.agent_explanation,
        iterations_used=task.iterations_used,
        model_name=task.model_name,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
        files=[_file_info(f) for f in files],
        references=[
            ReferenceInfo(
                id=r.id,
                source_name=r.source_name,
                quote_or_summary=r.quote_or_summary,
                used_for=r.used_for,
                created_at=r.created_at,
            )
            for r in extras["refs"]
        ],
        limitations=[
            LimitationInfo(id=l.id, text=l.text, created_at=l.created_at) for l in extras["lims"]
        ],
        generated_files=[
            GeneratedFileInfo(
                id=g.id,
                tool_call_id=g.tool_call_id,
                format=g.format,
                filename=g.filename,
                purpose=g.purpose,
                size_bytes=g.size_bytes,
                status=g.status,
                created_at=g.created_at,
            )
            for g in extras["gens"]
        ],
    )


@router.post("", response_model=TaskInfo)
def create_new_task(
    body: CreateTaskBody,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
) -> TaskInfo:
    if auth.role != "student":
        raise HTTPException(status_code=403, detail="只有學生身份可建立任務")
    task = create_task(db, auth.user_id, body.assignment_text)
    db.commit()
    db.refresh(task)
    return _task_to_info(task, [])


class TaskListItem(BaseModel):
    id: str
    status: str
    assignment_text: str
    agent_title: str | None
    iterations_used: int
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=list[TaskListItem])
def list_my_tasks(
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
) -> list[TaskListItem]:
    if auth.role != "student":
        return []
    tasks = list_user_tasks(db, auth.user_id)
    return [
        TaskListItem(
            id=t.id,
            status=t.status,
            assignment_text=t.assignment_text,
            agent_title=t.agent_title,
            iterations_used=t.iterations_used,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in tasks
    ]


@router.get("/{task_id}", response_model=TaskInfo)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
) -> TaskInfo:
    task = get_task_for_user(db, task_id, auth.user_id, auth.role)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到任務")
    files = list_task_files(db, task.id)
    extras = _load_task_extras(db, task.id)
    return _task_to_info(task, files, extras)


class RunTaskBody(BaseModel):
    model_name: str | None = Field(default=None, max_length=200)


@router.post("/{task_id}/run", response_model=TaskInfo)
def run_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    body: RunTaskBody | None = None,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
) -> TaskInfo:
    if auth.role != "student":
        raise HTTPException(status_code=403, detail="只有學生身份可執行任務")
    task = get_task_for_user(db, task_id, auth.user_id, auth.role)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到任務")
    if task.status == "processing":
        raise HTTPException(status_code=409, detail="任務已在執行中")

    if task.status in {"completed", "failed"}:
        reset_task_for_rerun(db, task)

    model_override = (body.model_name.strip() if body and body.model_name else None) or None
    db.commit()
    background_tasks.add_task(run_task_blocking, task.id, model_override)
    files = list_task_files(db, task.id)
    extras = _load_task_extras(db, task.id)
    return _task_to_info(task, files, extras)


class AgentToolCallInfo(BaseModel):
    id: str
    iteration: int
    tool_name: str
    status: str
    arguments_json: Any | None
    result_json: Any | None
    error_message: str | None
    duration_ms: int | None
    created_at: datetime


class ProgressEventInfo(BaseModel):
    id: str
    event_type: str
    message: str
    detail: Any | None
    created_at: datetime


class AgentTraceInfo(BaseModel):
    tool_calls: list[AgentToolCallInfo]
    progress_events: list[ProgressEventInfo]
    references: list[ReferenceInfo]
    limitations: list[LimitationInfo]
    generated_files: list[GeneratedFileInfo]


@router.delete("/{task_id}", status_code=204)
def delete_my_task(
    task_id: str,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
):
    task = get_task_for_user(db, task_id, auth.user_id, auth.role)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到任務")
    if auth.role != "admin" and task.user_id != auth.user_id:
        raise HTTPException(status_code=403, detail="無權刪除他人任務")
    delete_task(db, task)
    db.commit()
    return None


@router.get("/{task_id}/agent-trace", response_model=AgentTraceInfo)
def get_agent_trace(
    task_id: str,
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
) -> AgentTraceInfo:
    from app.services.progress_service import list_events

    task = get_task_for_user(db, task_id, auth.user_id, auth.role)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到任務")

    tool_call_rows = list(
        db.execute(
            select(AgentToolCall)
            .where(AgentToolCall.task_id == task.id)
            .order_by(AgentToolCall.created_at.asc(), AgentToolCall.iteration.asc())
        )
        .scalars()
        .all()
    )
    event_rows = list_events(db, task.id)
    extras = _load_task_extras(db, task.id)

    return AgentTraceInfo(
        tool_calls=[
            AgentToolCallInfo(
                id=c.id,
                iteration=c.iteration,
                tool_name=c.tool_name,
                status=c.status,
                arguments_json=c.arguments_json,
                result_json=c.result_json,
                error_message=c.error_message,
                duration_ms=c.duration_ms,
                created_at=c.created_at,
            )
            for c in tool_call_rows
        ],
        progress_events=[
            ProgressEventInfo(
                id=e.id,
                event_type=e.event_type,
                message=e.message,
                detail=e.detail,
                created_at=e.created_at,
            )
            for e in event_rows
        ],
        references=[
            ReferenceInfo(
                id=r.id,
                source_name=r.source_name,
                quote_or_summary=r.quote_or_summary,
                used_for=r.used_for,
                created_at=r.created_at,
            )
            for r in extras["refs"]
        ],
        limitations=[
            LimitationInfo(id=l.id, text=l.text, created_at=l.created_at)
            for l in extras["lims"]
        ],
        generated_files=[
            GeneratedFileInfo(
                id=g.id,
                tool_call_id=g.tool_call_id,
                format=g.format,
                filename=g.filename,
                purpose=g.purpose,
                size_bytes=g.size_bytes,
                status=g.status,
                created_at=g.created_at,
            )
            for g in extras["gens"]
        ],
    )


@router.post("/{task_id}/files", response_model=list[FileInfo])
async def upload_files(
    task_id: str,
    category: str = Form(..., description="course_material | assignment_file"),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    auth: AuthResult = Depends(get_current_session),
) -> list[FileInfo]:
    if auth.role != "student":
        raise HTTPException(status_code=403, detail="只有學生身份可上傳檔案")

    task = get_task_for_user(db, task_id, auth.user_id, auth.role)
    if task is None:
        raise HTTPException(status_code=404, detail="找不到任務")

    try:
        saved = await save_and_parse_uploads(db, task, files, category)
    except FileTooLargeError as exc:
        db.rollback()
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except InvalidCategoryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    return [
        FileInfo(
            id=f.id,
            file_category=f.file_category,
            original_filename=f.original_filename,
            file_type=f.file_type,
            file_size=f.file_size,
            parse_status=f.parse_status,
            summary=f.summary,
            error_message=f.error_message,
            created_at=f.created_at,
        )
        for f in saved
    ]
