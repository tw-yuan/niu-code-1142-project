from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import SHARED_LOGIN_PASSWORD, ADMIN_PASSWORD, SESSION_EXPIRE_MINUTES
from app.models.user import User
from app.models.session import Session


async def student_login(db: AsyncSession, display_name: str, password: str) -> Session | None:
    if password != SHARED_LOGIN_PASSWORD:
        return None

    result = await db.execute(
        select(User).where(User.display_name == display_name, User.role == "student")
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(display_name=display_name, role="student")
        db.add(user)
        await db.flush()

    session = Session(
        user_id=user.id,
        role="student",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=SESSION_EXPIRE_MINUTES),
    )
    db.add(session)
    await db.commit()
    return session


async def admin_login(db: AsyncSession, password: str) -> Session | None:
    if password != ADMIN_PASSWORD:
        return None

    result = await db.execute(
        select(User).where(User.role == "admin")
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(display_name="Admin", role="admin")
        db.add(user)
        await db.flush()

    session = Session(
        user_id=user.id,
        role="admin",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=SESSION_EXPIRE_MINUTES),
    )
    db.add(session)
    await db.commit()
    return session


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session and session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return None
    return session


async def logout(db: AsyncSession, session_id: str) -> None:
    result = await db.execute(
        select(Session).where(Session.id == session_id)
    )
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()
