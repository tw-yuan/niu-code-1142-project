import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import AdminConfig, Document, SystemEvent, TokenUsage, User, now_iso
from app.schemas import AdminConfigUpdate, AdminUserUpdate
from app.services.audit_service import AuditService
from app.services.cost_service import cost_stats
from app.services.privacy_service import PrivacyService


class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self) -> list[dict[str, Any]]:
        users = (await self.db.execute(select(User).order_by(User.created_at))).scalars().all()
        return [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "quota_mb": user.quota_mb,
                "token_quota": user.token_quota,
                "is_active": user.is_active,
                "created_at": user.created_at,
            }
            for user in users
        ]

    async def update_user(self, user_id: str, body: AdminUserUpdate, actor_id: str | None = None) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        next_role = body.role if body.role is not None else user.role
        next_active = body.is_active if body.is_active is not None else user.is_active
        if user.role == "admin" and (next_role != "admin" or not next_active):
            await self._ensure_another_active_admin(user.id)
        for field in ("quota_mb", "token_quota", "is_active", "role"):
            value = getattr(body, field)
            if value is not None:
                setattr(user, field, value)
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.user_update",
            user_id=actor_id,
            resource=f"user:{user_id}",
            detail=body.model_dump(exclude_none=True),
        )
        return {"ok": True}

    async def stats(self) -> dict[str, Any]:
        users = (await self.db.execute(select(func.count(User.id)))).scalar_one()
        documents = (await self.db.execute(select(func.count(Document.id)))).scalar_one()
        tokens = (
            await self.db.execute(select(func.coalesce(func.sum(TokenUsage.tokens_used), 0)))
        ).scalar_one()
        return {"users": users, "documents": documents, "tokens_used": tokens}

    async def get_llm_config(self) -> dict[str, Any]:
        config = await self._load_config()
        return _mask_keys(config)

    async def update_llm_config(self, body: AdminConfigUpdate, actor_id: str | None = None) -> dict[str, Any]:
        current = await self._load_config()
        incoming = body.model_dump(exclude_none=True)
        for key, value in incoming.items():
            current[key] = _merge_config(current.get(key, {}), value)
        row = (
            await self.db.execute(select(AdminConfig).where(AdminConfig.key == "llm_config"))
        ).scalar_one_or_none()
        payload = json.dumps(current, ensure_ascii=False)
        if row is None:
            self.db.add(AdminConfig(key="llm_config", value=payload))
        else:
            row.value = payload
            row.updated_at = now_iso()
        await self.db.commit()
        await AuditService(self.db).log(
            "admin.config_update",
            user_id=actor_id,
            resource="admin_config:llm_config",
            detail=incoming,
        )
        return _mask_keys(current)

    async def cost_stats(self) -> dict[str, Any]:
        return await cost_stats(self.db)

    async def reliability_stats(self) -> dict[str, Any]:
        since = (datetime.now(UTC) - timedelta(days=7)).isoformat()
        rows = (
            await self.db.execute(
                select(SystemEvent)
                .where(and_(SystemEvent.event_type == "llm_fallback", SystemEvent.created_at >= since))
                .order_by(desc(SystemEvent.created_at))
            )
        ).scalars().all()
        by_reason: dict[str, int] = {}
        daily: dict[str, int] = {}
        events = []
        for row in rows:
            detail = json.loads(row.detail)
            reason = detail.get("reason", "unknown")
            by_reason[reason] = by_reason.get(reason, 0) + 1
            day = row.created_at[:10]
            daily[day] = daily.get(day, 0) + 1
            events.append(
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "severity": row.severity,
                    "detail": detail,
                    "created_at": row.created_at,
                }
            )
        return {
            "fallback_count_7d": len(rows),
            "by_reason": by_reason,
            "daily_series": [{"date": key, "count": daily[key]} for key in sorted(daily)],
            "events": events[:50],
        }

    async def audit_logs(
        self,
        user_id: str | None = None,
        action: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        return await AuditService(self.db).list_logs(user_id, action, from_date, to_date, limit, offset)

    async def deletion_status(self) -> list[dict[str, Any]]:
        users = (
            await self.db.execute(
                select(User)
                .where(User.deletion_requested_at.is_not(None))
                .order_by(desc(User.deletion_requested_at))
            )
        ).scalars().all()
        return [
            {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "deletion_requested_at": user.deletion_requested_at,
                "deletion_scheduled_at": user.deletion_scheduled_at,
            }
            for user in users
        ]

    async def user_deletion_status(self, user_id: str) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return {
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "deletion_requested_at": user.deletion_requested_at,
            "deletion_scheduled_at": user.deletion_scheduled_at,
            "export_expires_at": user.export_expires_at,
        }

    async def force_purge_user(self, user_id: str, actor_id: str) -> dict[str, Any]:
        return await PrivacyService(self.db).force_purge(user_id, actor_id=actor_id)

    async def _load_config(self) -> dict[str, Any]:
        default = default_llm_config()
        row = (
            await self.db.execute(select(AdminConfig).where(AdminConfig.key == "llm_config"))
        ).scalar_one_or_none()
        if row is None:
            return default
        saved = json.loads(row.value)
        for key, value in saved.items():
            default.setdefault(key, {}).update(value)
        return default

    async def _ensure_another_active_admin(self, user_id: str) -> None:
        count = (
            await self.db.execute(
                select(func.count(User.id)).where(
                    and_(User.id != user_id, User.role == "admin", User.is_active == 1)
                )
            )
        ).scalar_one()
        if count == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot disable or demote the last active admin",
            )


def default_llm_config() -> dict[str, Any]:
    return {
        "chat": {
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "model": settings.LLM_CHAT_MODEL,
            "max_tokens": 4096,
            "temperature": 0.3,
        },
        "vision": {
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "model": settings.LLM_VISION_MODEL,
            "max_tokens": 2048,
        },
        "embedding": {
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "model": settings.LLM_EMBED_MODEL,
            "dimensions": 1536,
        },
        "cost_per_1k_tokens": {
            "gpt-4o": {"input": 0.0025, "output": 0.01},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "text-embedding-3-small": {"input": 0.00002, "output": 0.00002},
        },
        "fallback_providers": {},
    }


def _mask_keys(config: dict[str, Any]) -> dict[str, Any]:
    safe = json.loads(json.dumps(config))
    _mask_in_place(safe)
    return safe


def _mask_in_place(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "api_key" and item:
                value[key] = "********"
            else:
                _mask_in_place(item)
    elif isinstance(value, list):
        for item in value:
            _mask_in_place(item)


def _merge_config(current: Any, incoming: Any) -> Any:
    if isinstance(current, dict) and isinstance(incoming, dict):
        merged = json.loads(json.dumps(current))
        for key, value in incoming.items():
            if key == "api_key" and value == "********":
                continue
            merged[key] = _merge_config(merged.get(key), value)
        return merged
    if incoming == "********":
        return current
    return incoming
