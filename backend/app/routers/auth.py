from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_optional_session
from app.services.auth_service import (
    AuthError,
    AuthResult,
    login_admin,
    login_student,
    logout,
)
from app.utils.security import (
    SESSION_COOKIE_NAME,
    sign_session_id,
    verify_session_cookie,
)
from app.utils.validators import validate_nickname

router = APIRouter(prefix="/api/auth", tags=["auth"])


class StudentLoginBody(BaseModel):
    nickname: str = Field(..., min_length=1, max_length=40)
    password: str = Field(..., min_length=1)


class AdminLoginBody(BaseModel):
    password: str = Field(..., min_length=1)


class SessionInfo(BaseModel):
    role: str
    display_name: str | None
    user_id: str | None


def _set_session_cookie(response: Response, session_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sign_session_id(session_id),
        max_age=settings.session_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


@router.post("/student/login", response_model=SessionInfo)
def student_login(
    body: StudentLoginBody,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionInfo:
    try:
        nickname = validate_nickname(body.nickname)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        result = login_student(db, nickname, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    db.commit()
    _set_session_cookie(response, result.session_id)
    return SessionInfo(role=result.role, display_name=result.display_name, user_id=result.user_id)


@router.post("/admin/login", response_model=SessionInfo)
def admin_login(
    body: AdminLoginBody,
    response: Response,
    db: Session = Depends(get_db),
) -> SessionInfo:
    try:
        result = login_admin(db, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    db.commit()
    _set_session_cookie(response, result.session_id)
    return SessionInfo(role=result.role, display_name=result.display_name, user_id=result.user_id)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def do_logout(
    response: Response,
    db: Session = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
):
    session_id = verify_session_cookie(session_cookie) if session_cookie else None
    if session_id:
        logout(db, session_id)
        db.commit()
    _clear_session_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=SessionInfo | None)
def me(auth: AuthResult | None = Depends(get_optional_session)) -> SessionInfo | None:
    if auth is None:
        return None
    return SessionInfo(role=auth.role, display_name=auth.display_name, user_id=auth.user_id)
