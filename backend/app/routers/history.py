from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_student
from app.models.session import Session
from app.models.task import Task

router = APIRouter(prefix="/api/history", tags=["history"])


class HistoryItem(BaseModel):
    id: str
    assignment_text: str
    status: str
    input_summary: str | None
    output_formats: list
    created_at: str
    updated_at: str
    has_output: bool
    file_count: int


@router.get("", response_model=list[HistoryItem])
async def get_history(
    session: Session = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    if session.role == "admin":
        result = await db.execute(
            select(Task).order_by(Task.created_at.desc())
        )
    else:
        result = await db.execute(
            select(Task)
            .where(Task.user_id == session.user_id)
            .order_by(Task.created_at.desc())
        )

    tasks = result.scalars().all()
    items = []
    for t in tasks:
        items.append(HistoryItem(
            id=t.id,
            assignment_text=t.assignment_text[:100] + ("..." if len(t.assignment_text) > 100 else ""),
            status=t.status,
            input_summary=t.input_summary,
            output_formats=t.output_formats,
            created_at=t.created_at.isoformat(),
            updated_at=t.updated_at.isoformat(),
            has_output=t.output_text is not None,
            file_count=len(t.generated_files),
        ))
    return items
