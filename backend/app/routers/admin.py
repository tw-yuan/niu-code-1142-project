from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, require_admin
from app.models.tables import User
from app.schemas import AdminConfigUpdate, AdminUserUpdate
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).list_users()


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).update_user(user_id, body, actor_id=current_user.id)


@router.get("/stats")
async def stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).stats()


@router.get("/config")
async def get_config(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).get_llm_config()


@router.put("/config")
async def update_config(
    body: AdminConfigUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).update_llm_config(body, actor_id=current_user.id)


@router.get("/stats/cost")
async def cost_stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).cost_stats()


@router.get("/stats/reliability")
async def reliability_stats(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).reliability_stats()


@router.get("/audit-logs")
async def audit_logs(
    user_id: str | None = None,
    action: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).audit_logs(user_id, action, from_date, to_date, limit, offset)


@router.get("/deletions")
async def deletion_status(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).deletion_status()
