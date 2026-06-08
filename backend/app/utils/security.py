import secrets
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_shared_password(plain: str) -> bool:
    return plain == settings.shared_login_password


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=settings.session_expire_minutes)
