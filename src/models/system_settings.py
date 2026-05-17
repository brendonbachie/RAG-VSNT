"""SystemSettings ORM model and default values."""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base

# ── Default settings ───────────────────────────────────────────────────────────
DEFAULTS: dict[str, str] = {
    "ollama_model":                 "llama3",
    "session_timeout_seconds":      "28800",
    "indexing_status":              "idle",
    "indexing_started_at":          "",
    "indexing_last_completed_at":   "",
    "indexing_last_error":          "",
    "setup_complete":               "false",
}


class SystemSettings(Base):
    __tablename__ = "system_settings"

    key:                  Mapped[str]            = mapped_column(String(64), primary_key=True)
    value:                Mapped[str]            = mapped_column(String(1024), nullable=False)
    updated_at:           Mapped[datetime]       = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    updated_by_user_id:   Mapped[int | None]     = mapped_column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
