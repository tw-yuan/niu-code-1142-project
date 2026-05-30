from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._helpers import uuid_pk, created_at_col, updated_at_col


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = uuid_pk()
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    assignment_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    agent_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    agent_assignment_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    iterations_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
