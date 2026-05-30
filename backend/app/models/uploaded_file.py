from datetime import datetime

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._helpers import uuid_pk, created_at_col


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = uuid_pk()
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    file_category: Mapped[str] = mapped_column(String(40), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    parse_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_table_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = created_at_col()
