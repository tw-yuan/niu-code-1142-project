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
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
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
    await conn.run_sync(Base.metadata.create_all)

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

    existing_quizzes = {
        row[1] for row in (await conn.execute(text("PRAGMA table_info(quizzes)"))).fetchall()
    }
    if "course_id" not in existing_quizzes:
        await conn.execute(text("ALTER TABLE quizzes ADD COLUMN course_id TEXT"))

    existing_course_quizzes = {
        row[1] for row in (await conn.execute(text("PRAGMA table_info(course_quizzes)"))).fetchall()
    }
    course_quiz_columns = {
        "available_from": "TEXT",
        "answer_visible_at": "TEXT",
        "attempt_limit": "INTEGER",
    }
    for column, column_type in course_quiz_columns.items():
        if column not in existing_course_quizzes:
            await conn.execute(
                text(f"ALTER TABLE course_quizzes ADD COLUMN {column} {column_type}")
            )

    existing_course_documents = {
        row[1]
        for row in (await conn.execute(text("PRAGMA table_info(course_documents)"))).fetchall()
    }
    course_document_columns = {
        "is_active": "INTEGER NOT NULL DEFAULT 1",
        "removed_at": "TEXT",
        "removed_by": "TEXT",
    }
    for column, column_type in course_document_columns.items():
        if column not in existing_course_documents:
            await conn.execute(
                text(f"ALTER TABLE course_documents ADD COLUMN {column} {column_type}")
            )

    existing_question_bank = (
        await conn.execute(text("PRAGMA table_info(course_question_bank_items)"))
    ).fetchall()
    if existing_question_bank:
        question_bank_columns = {
            "review_note": "TEXT",
            "reviewed_by": "TEXT",
            "reviewed_at": "TEXT",
        }
        existing_question_bank_columns = {row[1] for row in existing_question_bank}
        for column, column_type in question_bank_columns.items():
            if column not in existing_question_bank_columns:
                await conn.execute(
                    text(
                        f"ALTER TABLE course_question_bank_items ADD COLUMN {column} {column_type}"
                    )
                )

    existing_usage = {
        row[1] for row in (await conn.execute(text("PRAGMA table_info(token_usage)"))).fetchall()
    }
    usage_columns = {
        "input_tokens": "INTEGER NOT NULL DEFAULT 0",
        "output_tokens": "INTEGER NOT NULL DEFAULT 0",
        "image_count": "INTEGER NOT NULL DEFAULT 0",
        "page_count": "INTEGER NOT NULL DEFAULT 0",
        "provider": "TEXT",
        "request_id": "TEXT",
        "unit_price_snapshot": "TEXT NOT NULL DEFAULT '{}'",
        "cost_usd": "FLOAT NOT NULL DEFAULT 0.0",
    }
    for column, column_type in usage_columns.items():
        if column not in existing_usage:
            await conn.execute(text(f"ALTER TABLE token_usage ADD COLUMN {column} {column_type}"))
