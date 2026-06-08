from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Annotated

from app.database import get_db
from app.services.auth_service import login, logout
from app.deps import get_current_user, get_current_session
from app.models.user import User
from app.models.session import Session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    nickname: str
    password: str


class UserResponse(BaseModel):
    id: int
    nickname: str

    model_config = {"from_attributes": True}


@router.post("/login")
async def auth_login(
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await login(db, body.nickname.strip(), body.password)
    if not session:
        raise HTTPException(status_code=401, detail="密碼錯誤")
    response.set_cookie(
        key="session_token",
        value=session.token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24,
    )
    return {"message": "ok", "nickname": body.nickname.strip()}


@router.post("/logout")
async def auth_logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    session: Annotated[Session, Depends(get_current_session)],
):
    await logout(db, session.token)
    response.delete_cookie("session_token")
    return {"message": "ok"}


@router.get("/me", response_model=UserResponse)
async def auth_me(user: Annotated[User, Depends(get_current_user)]):
    return user
