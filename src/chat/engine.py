"""Chat engine singleton — wraps the existing RAG pipeline."""

import threading
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.system_settings import SystemSettings

_lock = threading.Lock()
_engine_instance = None
_engine_model: str | None = None


def invalidate_engine() -> None:
    """Force rebuild on next get_engine() call (e.g. after model change)."""
    global _engine_instance, _engine_model
    with _lock:
        _engine_instance = None
        _engine_model = None


def get_engine(active_model: str):
    """Return cached engine or rebuild if model changed."""
    global _engine_instance, _engine_model

    with _lock:
        if _engine_instance is not None and _engine_model == active_model:
            return _engine_instance

        # Import here to avoid circular imports and to defer heavy loading
        from rag_vsnt_offline import build_settings, load_or_build_index, build_chat_engine
        import rag_vsnt_offline as rag

        rag.OLLAMA_MODEL = active_model
        build_settings()
        index = load_or_build_index()
        _engine_instance = build_chat_engine(index)
        _engine_model = active_model

    return _engine_instance


async def get_active_model(db: AsyncSession) -> str:
    result = await db.execute(
        select(SystemSettings).where(SystemSettings.key == "ollama_model")
    )
    row = result.scalar_one_or_none()
    return row.value if row else "llama3"
