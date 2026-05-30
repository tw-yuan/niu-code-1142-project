from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._helpers import uuid_pk, created_at_col, updated_at_col


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[str] = uuid_pk()
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = updated_at_col()


class SystemSettingHistory(Base):
    __tablename__ = "system_setting_history"

    id: Mapped[str] = uuid_pk()
    setting_id: Mapped[str] = mapped_column(String(36), ForeignKey("system_settings.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = created_at_col()
