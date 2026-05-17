"""AuditEvent ORM model and event type constants."""

import json
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base

# ── Event type constants ───────────────────────────────────────────────────────
LOGIN_SUCCESS    = "login_success"
LOGIN_FAILURE    = "login_failure"
LOGOUT           = "logout"
QUERY            = "query"
DOCUMENT_UPLOADED = "document_uploaded"
DOCUMENT_DELETED  = "document_deleted"
INDEX_TRIGGERED   = "index_triggered"
MODEL_CHANGED     = "model_changed"
USER_CREATED      = "user_created"
USER_DEACTIVATED  = "user_deactivated"
USER_REACTIVATED  = "user_reactivated"
USER_DELETED      = "user_deleted"
SETTINGS_CHANGED  = "settings_changed"


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id:                Mapped[int]            = mapped_column(primary_key=True, autoincrement=True)
    event_type:        Mapped[str]            = mapped_column(String(32), nullable=False)
    user_id:           Mapped[int | None]     = mapped_column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    username_snapshot: Mapped[str]            = mapped_column(String(64), nullable=False)
    payload:           Mapped[str]            = mapped_column(Text, nullable=False, default="{}")
    created_at:        Mapped[datetime]       = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_audit_event_created_at", "created_at"),
    )

    def payload_dict(self) -> dict:
        return json.loads(self.payload)
