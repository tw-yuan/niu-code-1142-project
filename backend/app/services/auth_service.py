from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import User, UserSession
from app.utils.security import (
    compare_password,
    is_expired,
    session_expiry,
)


ROLE_STUDENT = "student"
ROLE_ADMIN = "admin"


class AuthError(Exception):
    """Raised when login fails."""


@dataclass
class AuthResult:
    session_id: str
    user_id: str | None
    role: str
    display_name: str | None


def _find_or_create_student_user(db: Session, nickname: str) -> User:
    stmt = select(User).where(User.role == ROLE_STUDENT, User.display_name == nickname)
    user = db.execute(stmt).scalar_one_or_none()
    if user is None:
        user = User(role=ROLE_STUDENT, display_name=nickname, auth_provider="password")
        db.add(user)
        db.flush()
    return user


def login_student(db: Session, nickname: str, password: str) -> AuthResult:
    settings = get_settings()
    if not compare_password(password, settings.shared_login_password):
        raise AuthError("密碼錯誤，請重新輸入")

    user = _find_or_create_student_user(db, nickname)
    session = UserSession(
        user_id=user.id,
        role=ROLE_STUDENT,
        expires_at=session_expiry(),
    )
    db.add(session)
    db.flush()
    return AuthResult(
        session_id=session.id,
        user_id=user.id,
        role=ROLE_STUDENT,
        display_name=user.display_name,
    )


def login_admin(db: Session, password: str) -> AuthResult:
    settings = get_settings()
    if not compare_password(password, settings.admin_password):
        raise AuthError("密碼錯誤，請重新輸入")

    session = UserSession(
        user_id=None,
        role=ROLE_ADMIN,
        expires_at=session_expiry(),
    )
    db.add(session)
    db.flush()
    return AuthResult(
        session_id=session.id,
        user_id=None,
        role=ROLE_ADMIN,
        display_name="Admin",
    )


def logout(db: Session, session_id: str) -> None:
    session = db.get(UserSession, session_id)
    if session is not None:
        db.delete(session)


def resolve_session(db: Session, session_id: str | None) -> AuthResult | None:
    if not session_id:
        return None
    session = db.get(UserSession, session_id)
    if session is None or is_expired(session.expires_at):
        if session is not None:
            db.delete(session)
        return None

    display_name: str | None
    if session.user_id is None:
        display_name = "Admin"
    else:
        user = db.get(User, session.user_id)
        display_name = user.display_name if user else None

    return AuthResult(
        session_id=session.id,
        user_id=session.user_id,
        role=session.role,
        display_name=display_name,
    )
