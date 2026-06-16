import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import AdminConfig, Document, TokenUsage, User, now_iso
from app.schemas import AdminConfigUpdate, AdminUserUpdate


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

    async def update_user(self, user_id: str, body: AdminUserUpdate) -> dict[str, Any]:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            from fastapi import HTTPException, status

            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        for field in ("quota_mb", "token_quota", "is_active", "role"):
            value = getattr(body, field)
            if value is not None:
                setattr(user, field, value)
        await self.db.commit()
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

    async def update_llm_config(self, body: AdminConfigUpdate) -> dict[str, Any]:
        current = await self._load_config()
        incoming = body.model_dump(exclude_none=True)
        for key, value in incoming.items():
            current.setdefault(key, {}).update(value)
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
        return _mask_keys(current)

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
    }


def _mask_keys(config: dict[str, Any]) -> dict[str, Any]:
    safe = json.loads(json.dumps(config))
    for value in safe.values():
        if isinstance(value, dict) and value.get("api_key"):
            value["api_key"] = "********"
    return safe

