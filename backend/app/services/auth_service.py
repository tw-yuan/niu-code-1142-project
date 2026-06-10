from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from app.models.user import User
from app.models.session import Session
from app.utils.security import (
    verify_admin_password,
    verify_shared_password,
    generate_session_token,
    session_expiry,
)


async def login(db: AsyncSession, nickname: str, password: str) -> Session | None:
    is_admin = verify_admin_password(password)
    if not is_admin and not verify_shared_password(password):
        return None

    result = await db.execute(select(User).where(User.nickname == nickname))
    user = result.scalar_one_or_none()
    if not user:
        user = User(nickname=nickname, role="admin" if is_admin else "student")
        db.add(user)
        await db.flush()
    elif is_admin and user.role != "admin":
        user.role = "admin"

    token = generate_session_token()
    session = Session(user_id=user.id, token=token, expires_at=session_expiry())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, token: str) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.token == token)
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    now = datetime.now(timezone.utc)
    expires = session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
    if expires < now:
        await db.delete(session)
        await db.commit()
        return None
    return session


async def logout(db: AsyncSession, token: str) -> None:
    result = await db.execute(select(Session).where(Session.token == token))
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()
