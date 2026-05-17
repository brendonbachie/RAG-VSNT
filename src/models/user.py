"""User ORM model."""

from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class User(Base):
    __tablename__ = "user"

    id:              Mapped[int]            = mapped_column(primary_key=True, autoincrement=True)
    username:        Mapped[str]            = mapped_column(String(64), nullable=False)
    password_hash:   Mapped[str]            = mapped_column(String(256), nullable=False)
    role:            Mapped[str]            = mapped_column(String(16), nullable=False)  # "admin" | "operator"
    is_active:       Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    created_at:      Mapped[datetime]       = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        # Case-insensitive unique constraint on username
        {"sqlite_autoincrement": True},
    )
