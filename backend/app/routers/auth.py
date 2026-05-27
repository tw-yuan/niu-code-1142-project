from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.auth_service import student_login, admin_login, logout
from app.dependencies import get_current_session
from app.models.session import Session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class StudentLoginRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class AdminLoginRequest(BaseModel):
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    success: bool
    role: str
    display_name: str
    user_id: str


class MeResponse(BaseModel):
    user_id: str
    display_name: str
    role: str


@router.post("/student/login", response_model=LoginResponse)
async def api_student_login(
    req: StudentLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    session = await student_login(db, req.display_name.strip(), req.password)
    if not session:
        raise HTTPException(status_code=401, detail="密碼錯誤，請重新輸入")
    response.set_cookie(
        key="session_id",
        value=session.id,
        httponly=True,
        samesite="lax",
        max_age=session.expires_at.timestamp() - session.created_at.timestamp(),
    )
    return LoginResponse(
        success=True,
        role="student",
        display_name=req.display_name.strip(),
        user_id=session.user_id,
    )


@router.post("/admin/login", response_model=LoginResponse)
async def api_admin_login(
    req: AdminLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    session = await admin_login(db, req.password)
    if not session:
        raise HTTPException(status_code=401, detail="密碼錯誤，請重新輸入")
    response.set_cookie(
        key="session_id",
        value=session.id,
        httponly=True,
        samesite="lax",
        max_age=session.expires_at.timestamp() - session.created_at.timestamp(),
    )
    return LoginResponse(
        success=True,
        role="admin",
        display_name="Admin",
        user_id=session.user_id,
    )


@router.post("/logout")
async def api_logout(
    response: Response,
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    await logout(db, session.id)
    response.delete_cookie("session_id")
    return {"success": True}


@router.get("/me", response_model=MeResponse)
async def api_me(
    session: Session = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == session.user_id))
    user = result.scalar_one()
    return MeResponse(
        user_id=user.id,
        display_name=user.display_name,
        role=session.role,
    )
