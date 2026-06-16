from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.tables import Base

engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.db_path.mkdir(parents=True, exist_ok=True)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if settings.DATABASE_URL.startswith("sqlite"):
            await _ensure_sqlite_columns(conn)


async def _ensure_sqlite_columns(conn) -> None:
    existing_users = {
        row[1] for row in (await conn.execute(text("PRAGMA table_info(users)"))).fetchall()
    }
    user_columns = {
        "deletion_requested_at": "TEXT",
        "deletion_confirm_code": "TEXT",
        "deletion_scheduled_at": "TEXT",
        "export_path": "TEXT",
        "export_expires_at": "TEXT",
    }
    for column, column_type in user_columns.items():
        if column not in existing_users:
            await conn.execute(text(f"ALTER TABLE users ADD COLUMN {column} {column_type}"))

    existing_sessions = {
        row[1] for row in (await conn.execute(text("PRAGMA table_info(chat_sessions)"))).fetchall()
    }
    if "course_id" not in existing_sessions:
        await conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN course_id TEXT"))
