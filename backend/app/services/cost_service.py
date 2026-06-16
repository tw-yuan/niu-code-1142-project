from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import AdminConfig, TokenUsage, User

DEFAULT_COST_PER_1K = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.00002},
}


async def load_cost_config(db: AsyncSession) -> dict[str, Any]:
    config = DEFAULT_COST_PER_1K.copy()
    row = (
        await db.execute(select(AdminConfig).where(AdminConfig.key == "llm_config"))
    ).scalar_one_or_none()
    if row:
        saved = json.loads(row.value)
        config.update(saved.get("cost_per_1k_tokens", {}))
    return config


def estimate_cost(tokens: int, model: str, feature: str, cost_config: dict[str, Any]) -> float:
    pricing = cost_config.get(model) or cost_config.get(_model_family(model), {})
    if isinstance(pricing, (int, float)):
        rate = float(pricing)
    elif feature in {"embedding", "embed"}:
        rate = float(pricing.get("input", pricing.get("output", 0.0)))
    else:
        rate = float(pricing.get("output", pricing.get("input", 0.0)))
    return round(tokens / 1000 * rate, 6)


def estimate_usage_cost(
    input_tokens: int,
    output_tokens: int,
    model: str,
    feature: str,
    cost_config: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    pricing = cost_config.get(model) or cost_config.get(_model_family(model), {})
    if isinstance(pricing, (int, float)):
        input_rate = output_rate = float(pricing)
        snapshot: dict[str, Any] = {"input": input_rate, "output": output_rate}
    else:
        input_rate = float(pricing.get("input", pricing.get("output", 0.0)))
        output_rate = float(pricing.get("output", pricing.get("input", 0.0)))
        snapshot = {"input": input_rate, "output": output_rate}
    if feature in {"embedding", "embed"}:
        output_tokens = 0
    cost = input_tokens / 1000 * input_rate + output_tokens / 1000 * output_rate
    return round(cost, 6), snapshot


async def monthly_usage(db: AsyncSession, user_id: str) -> int:
    start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return int(
        (
            await db.execute(
                select(func.coalesce(func.sum(TokenUsage.tokens_used), 0)).where(
                    and_(TokenUsage.user_id == user_id, TokenUsage.created_at >= start.isoformat())
                )
            )
        ).scalar_one()
    )


async def quota_status(db: AsyncSession, user: User) -> dict[str, Any]:
    used = await monthly_usage(db, user.id)
    percent = int(used / user.token_quota * 100) if user.token_quota else 100
    status_value = "exceeded" if percent >= 100 else "warning" if percent >= 80 else "ok"
    return {
        "token_used_this_month": used,
        "quota_percent": percent,
        "quota_status": status_value,
    }


async def check_quota(db: AsyncSession | None, user_id: str | None) -> None:
    if db is None or not user_id:
        return
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        return
    used = await monthly_usage(db, user.id)
    if used >= user.token_quota:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "quota_exceeded",
                "message": "本月 token 配額已用完，請聯絡管理員",
                "used": used,
                "limit": user.token_quota,
            },
        )


async def cost_stats(db: AsyncSession) -> dict[str, Any]:
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    since_30 = today_start - timedelta(days=29)
    cost_config = await load_cost_config(db)
    rows = (
        await db.execute(
            select(TokenUsage, User.username)
            .join(User, User.id == TokenUsage.user_id)
            .where(TokenUsage.created_at >= since_30.isoformat())
        )
    ).all()

    today_by_feature: dict[str, float] = defaultdict(float)
    month_by_feature: dict[str, float] = defaultdict(float)
    top_users: dict[str, dict[str, Any]] = {}
    daily_series: dict[str, float] = defaultdict(float)

    for usage, username in rows:
        cost = (
            float(usage.cost_usd)
            if usage.cost_usd
            else estimate_cost(usage.tokens_used, usage.model, usage.feature, cost_config)
        )
        created = _parse_dt(usage.created_at)
        day_key = created.date().isoformat()
        daily_series[day_key] += cost
        if created >= month_start:
            month_by_feature[usage.feature] += cost
            top_users.setdefault(
                usage.user_id,
                {"user_id": usage.user_id, "username": username, "total_usd": 0.0},
            )
            top_users[usage.user_id]["total_usd"] += cost
        if created >= today_start:
            today_by_feature[usage.feature] += cost

    series = []
    for i in range(30):
        day = (since_30 + timedelta(days=i)).date().isoformat()
        series.append({"date": day, "total_usd": round(daily_series[day], 6)})

    top = sorted(top_users.values(), key=lambda item: item["total_usd"], reverse=True)[:10]
    for item in top:
        item["total_usd"] = round(item["total_usd"], 6)

    return {
        "today": {
            "total_usd": round(sum(today_by_feature.values()), 6),
            "by_feature": {k: round(v, 6) for k, v in today_by_feature.items()},
        },
        "this_month": {
            "total_usd": round(sum(month_by_feature.values()), 6),
            "by_feature": {k: round(v, 6) for k, v in month_by_feature.items()},
        },
        "top_users": top,
        "daily_series": series,
    }


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _model_family(model: str) -> str:
    if "/" in model:
        return model.rsplit("/", 1)[-1]
    return model
