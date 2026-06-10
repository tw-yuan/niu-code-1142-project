from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from app.database import Base


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    direction_key: Mapped[str] = mapped_column(String(50))
    direction_label: Mapped[str] = mapped_column(String(100))
    direction_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    direction_emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="learning_sessions")  # noqa
    document: Mapped["Document"] = relationship(back_populates="learning_sessions")  # noqa
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="learning_session", cascade="all, delete-orphan")  # noqa
