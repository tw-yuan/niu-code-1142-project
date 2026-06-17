from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.services.generation_service import GenerationService

router = APIRouter(prefix="/generation", tags=["generation"])


@router.get("/tasks")
async def active_generation_tasks(
    kind: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GenerationService(db).active_tasks(current_user.id, kind=kind)


@router.get("/tasks/{task_id}")
async def get_generation_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GenerationService(db).get_task(current_user.id, task_id)
