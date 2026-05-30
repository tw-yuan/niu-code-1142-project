from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_session
from app.services.auth_service import AuthResult
from app.services.task_service import (
    FileTooLargeError,
    InvalidCategoryError,
    create_task,
    get_task_for_user,
    list_task_files,
    list_user_tasks,
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


def _task_to_info(task, files) -> TaskInfo:
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
        files=[
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
            for f in files
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
    return _task_to_info(task, files)


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
