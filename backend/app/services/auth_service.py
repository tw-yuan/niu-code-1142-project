from datetime import timedelta

from fastapi import HTTPException, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tables import User
from app.schemas import LoginRequest, PasswordChangeRequest, ProfileUpdateRequest, RegisterRequest
from app.services.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, body: RegisterRequest) -> User:
        existing_username = (
            await self.db.execute(
                select(User.id).where(User.username == body.username)
            )
        ).scalar_one_or_none()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )
        existing_email = (
            await self.db.execute(select(User.id).where(User.email == body.email))
        ).scalar_one_or_none()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        user_count = (await self.db.execute(select(func.count(User.id)))).scalar_one()
        role = "admin" if user_count == 0 else "student"
        user = User(
            username=body.username,
            email=body.email,
            password_hash=hash_password(body.password),
            role=role,
            quota_mb=settings.DEFAULT_USER_QUOTA_MB,
            token_quota=settings.DEFAULT_TOKEN_QUOTA,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, body: LoginRequest) -> User:
        user = (
            await self.db.execute(
                select(User).where(
                    or_(User.username == body.identifier, User.email == body.identifier)
                )
            )
        ).scalar_one_or_none()
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")
        return user

    async def user_from_refresh_token(self, token: str) -> User:
        payload = decode_token(token, "refresh")
        user = (await self.db.execute(select(User).where(User.id == payload["sub"]))).scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user

    async def update_profile(self, user_id: str, body: ProfileUpdateRequest) -> User:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if body.username is not None and body.username != user.username:
            existing = (
                await self.db.execute(
                    select(User.id).where(and_(User.username == body.username, User.id != user_id))
                )
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
            user.username = body.username
        if body.email is not None and body.email != user.email:
            existing = (
                await self.db.execute(
                    select(User.id).where(and_(User.email == body.email, User.id != user_id))
                )
            ).scalar_one_or_none()
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
            user.email = str(body.email)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(self, user_id: str, body: PasswordChangeRequest) -> None:
        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not verify_password(body.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")
        user.password_hash = hash_password(body.new_password)
        await self.db.commit()


def issue_tokens(response: Response, user: User) -> str:
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
        path="/",
    )
    return access_token


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie("refresh_token", path="/", secure=settings.COOKIE_SECURE, samesite="lax")
