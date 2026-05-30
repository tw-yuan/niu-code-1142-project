from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.auth_service import AuthResult, ROLE_ADMIN, resolve_session
from app.utils.security import SESSION_COOKIE_NAME, verify_session_cookie


def get_current_session(
    db: Session = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AuthResult:
    session_id = verify_session_cookie(session_cookie) if session_cookie else None
    auth = resolve_session(db, session_id)
    if auth is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="尚未登入或登入已過期",
        )
    return auth


def get_optional_session(
    db: Session = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> AuthResult | None:
    session_id = verify_session_cookie(session_cookie) if session_cookie else None
    return resolve_session(db, session_id)


def require_admin(auth: AuthResult = Depends(get_current_session)) -> AuthResult:
    if auth.role != ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理者權限",
        )
    return auth
