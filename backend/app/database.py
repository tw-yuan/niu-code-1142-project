from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

DATABASE_URL = f"sqlite+aiosqlite:///{settings.data_dir}/app.db"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    from app.models import user, session, document, learning_session, chat_message, system_setting  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.exec_driver_sql("PRAGMA busy_timeout=5000")
        await _ensure_sqlite_columns(conn)


async def _ensure_sqlite_columns(conn) -> None:
    await _add_column_if_missing(conn, "users", "role", "VARCHAR(20) DEFAULT 'student'")
    await _add_column_if_missing(conn, "documents", "parse_status", "VARCHAR(20) DEFAULT 'ready'")
    await _add_column_if_missing(conn, "documents", "error_message", "TEXT")


async def _add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    rows = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
    existing = {row[1] for row in rows}
    if column not in existing:
        await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
