from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_db_url = _settings.database_url

if _db_url.startswith("sqlite"):
    db_path_str = _db_url.replace("sqlite:///", "")
    Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        _db_url,
        connect_args={"check_same_thread": False},
        future=True,
    )
else:
    engine = create_engine(_db_url, future=True)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app import models  # noqa: F401 — ensure all models are registered
    Base.metadata.create_all(bind=engine)
