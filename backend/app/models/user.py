from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models._helpers import uuid_pk, created_at_col, updated_at_col


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = uuid_pk()
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
    auth_provider: Mapped[str] = mapped_column(String(40), nullable=False, default="password")
    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()
