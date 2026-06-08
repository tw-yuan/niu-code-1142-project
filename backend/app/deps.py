from fastapi import Depends, HTTPException, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from app.database import get_db
from app.models.user import User
from app.models.session import Session
from app.services.auth_service import get_session


async def get_current_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    session_token: Annotated[str | None, Cookie()] = None,
) -> Session:
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = await get_session(db, session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return session


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[Session, Depends(get_current_session)],
) -> User:
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == session.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
