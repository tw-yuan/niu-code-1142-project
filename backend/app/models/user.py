from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nickname: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="student")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa
    documents: Mapped[list["Document"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa
    learning_sessions: Mapped[list["LearningSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa
