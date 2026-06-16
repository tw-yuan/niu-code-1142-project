import json
from typing import Any

from fastapi import Request
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import AuditLog

SENSITIVE_KEYS = {"password", "api_key", "secret", "token", "refresh_token"}


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        user_id: str | None = None,
        resource: str | None = None,
        request: Request | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        ip_address = None
        user_agent = None
        if request is not None:
            forwarded = request.headers.get("x-forwarded-for")
            ip_address = forwarded.split(",", 1)[0].strip() if forwarded else request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
        self.db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                resource=resource,
                ip_address=ip_address,
                user_agent=user_agent,
                detail=json.dumps(_sanitize(detail or {}), ensure_ascii=False),
            )
        )
        await self.db.commit()

    async def list_logs(
        self,
        user_id: str | None = None,
        action: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        conditions = []
        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if action:
            conditions.append(AuditLog.action == action)
        if from_date:
            conditions.append(AuditLog.created_at >= from_date)
        if to_date:
            conditions.append(AuditLog.created_at <= to_date)
        stmt = select(AuditLog)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        rows = (
            await self.db.execute(
                stmt.order_by(desc(AuditLog.created_at)).limit(limit).offset(offset)
            )
        ).scalars().all()
        return [
            {
                "id": row.id,
                "user_id": row.user_id,
                "action": row.action,
                "resource": row.resource,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "detail": json.loads(row.detail),
                "created_at": row.created_at,
            }
            for row in rows
        ]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if key.lower() in SENSITIVE_KEYS else _sanitize(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value

