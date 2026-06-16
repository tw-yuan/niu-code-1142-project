import asyncio

from sqlalchemy import select

from app.models.database import SessionLocal
from app.models.tables import User
from app.services.cost_service import quota_status
from app.services.privacy_service import PrivacyService
from app.services.ws_manager import push_to_user
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.maintenance_tasks.push_quota_warnings")
def push_quota_warnings() -> None:
    asyncio.run(_push_quota_warnings_async())


async def _push_quota_warnings_async() -> None:
    async with SessionLocal() as db:
        users = (
            await db.execute(select(User).where(User.is_active == 1))
        ).scalars().all()
        for user in users:
            status = await quota_status(db, user)
            if status["quota_percent"] >= 80:
                await push_to_user(
                    user.id,
                    {
                        "type": "quota_warning",
                        "quota_percent": status["quota_percent"],
                        "quota_status": status["quota_status"],
                        "token_used_this_month": status["token_used_this_month"],
                        "token_quota": user.token_quota,
                    },
                )


@celery_app.task(name="app.tasks.maintenance_tasks.purge_due_users")
def purge_due_users() -> int:
    return asyncio.run(_purge_due_users_async())


async def _purge_due_users_async() -> int:
    async with SessionLocal() as db:
        return await PrivacyService(db).purge_due_users()
