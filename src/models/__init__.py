"""ORM model registry — import here to register all models with Base.metadata."""

from src.db.database import Base  # noqa: re-export Base so init_db can find it
from src.models.user import User
from src.models.audit_event import AuditEvent
from src.models.system_settings import SystemSettings, DEFAULTS

__all__ = ["Base", "User", "AuditEvent", "SystemSettings", "DEFAULTS"]
