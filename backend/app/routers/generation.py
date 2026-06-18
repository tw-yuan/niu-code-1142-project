from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.services.generation_service import GenerationService

router = APIRouter(prefix="/generation", tags=["generation"])


@router.get("/tasks")
async def active_generation_tasks(
    kind: str | None = None,
    status_value: str | None = Query(default=None, alias="status"),
    active_only: bool = True,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GenerationService(db).list_tasks(
        current_user.id,
        kind=kind,
        status_value=status_value,
        active_only=active_only,
        limit=limit,
    )


@router.get("/tasks/{task_id}")
async def get_generation_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GenerationService(db).get_task(current_user.id, task_id)
