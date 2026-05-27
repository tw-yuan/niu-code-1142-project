import hashlib
import secrets


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def mask_secret(value: str) -> str:
    if not value or len(value) <= 8:
        return "****"
    return value[:4] + "*" * (len(value) - 8) + value[-4:]
