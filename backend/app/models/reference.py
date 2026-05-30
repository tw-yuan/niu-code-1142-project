from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._helpers import uuid_pk, created_at_col


class Reference(Base):
    __tablename__ = "references"

    id: Mapped[str] = uuid_pk()
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(String(500), nullable=False)
    quote_or_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    used_for: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = created_at_col()
