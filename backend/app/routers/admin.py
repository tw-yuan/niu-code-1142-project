from fastapi import APIRouter, Depends
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
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).update_user(user_id, body)


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
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await AdminService(db).update_llm_config(body)

