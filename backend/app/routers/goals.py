from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.tables import User
from app.schemas import GoalCreate, GoalUpdate
from app.services.goals_service import GoalsService

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("")
async def create_goal(
    body: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GoalsService(db).create(current_user.id, body)


@router.get("")
async def list_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GoalsService(db).list(current_user.id)


@router.get("/today")
async def today_tasks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GoalsService(db).today(current_user.id)


@router.put("/{goal_id}")
async def update_goal(
    goal_id: str,
    body: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await GoalsService(db).update(current_user.id, goal_id, body)


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await GoalsService(db).delete(current_user.id, goal_id)
    return {"ok": True}
