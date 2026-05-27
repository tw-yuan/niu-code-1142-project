import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(SAEnum("student", "admin", name="user_role"), nullable=False, default="student")
    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="password")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tasks = relationship("Task", back_populates="user", lazy="selectin")
    sessions = relationship("Session", back_populates="user", lazy="selectin")
