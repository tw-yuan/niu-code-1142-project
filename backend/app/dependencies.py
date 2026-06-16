import time
import uuid
from collections.abc import AsyncGenerator

import chromadb
import redis.asyncio as redis
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_session
from app.models.tables import User
from app.services.security import decode_token

security = HTTPBearer(auto_error=False)
_chroma_client: chromadb.ClientAPI | None = None
_redis_client: redis.Redis | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


def get_chroma() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        settings.data_path.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_PATH)
    return _chroma_client


def get_documents_collection(client: chromadb.ClientAPI):
    return client.get_or_create_collection(
        name="documents",
        metadata={"hnsw:space": "cosine"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(credentials.credentials, "access")
    stmt = select(User).where(User.id == payload["sub"])
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials, "access")
    except Exception:
        return None
    user = (await db.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return current_user


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def rate_limit(key_prefix: str, limit: int, window_seconds: int):
    async def _check(
        request: Request,
        response: Response,
        current_user: User | None = Depends(get_current_user_optional),
    ) -> None:
        if current_user and current_user.role == "admin":
            return
        identifier = current_user.id if current_user else _client_ip(request)
        key = f"rl:{key_prefix}:{identifier}"
        now = time.time()
        reset_at = int(now + window_seconds)
        try:
            client = get_redis()
            await client.zremrangebyscore(key, 0, now - window_seconds)
            count = await client.zcard(key)
            if count >= limit:
                oldest = await client.zrange(key, 0, 0, withscores=True)
                retry_after = max(1, int(oldest[0][1] + window_seconds - now)) if oldest else window_seconds
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(int(now + retry_after))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "code": "rate_limited",
                        "message": "請求過於頻繁，請稍後再試",
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            await client.zadd(key, {f"{now}:{uuid.uuid4()}": now})
            await client.expire(key, window_seconds)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count - 1))
            response.headers["X-RateLimit-Reset"] = str(reset_at)
        except HTTPException:
            raise
        except Exception:
            return

    return Depends(_check)


def get_token_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    token = request.query_params.get("token")
    return token


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"
