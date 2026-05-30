import hmac
import secrets
from datetime import datetime, timedelta, timezone

from itsdangerous import BadSignature, URLSafeSerializer

from app.config import get_settings


SESSION_COOKIE_NAME = "niu_ai_session"
_SALT = "session-cookie"


def _serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().app_secret_key, salt=_SALT)


def sign_session_id(session_id: str) -> str:
    return _serializer().dumps(session_id)


def verify_session_cookie(value: str) -> str | None:
    try:
        result = _serializer().loads(value)
    except BadSignature:
        return None
    if not isinstance(result, str):
        return None
    return result


def compare_password(provided: str, expected: str) -> bool:
    if not provided or not expected:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def new_token() -> str:
    return secrets.token_urlsafe(24)


def session_expiry() -> datetime:
    minutes = get_settings().session_expire_minutes
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def is_expired(dt: datetime) -> bool:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= dt
