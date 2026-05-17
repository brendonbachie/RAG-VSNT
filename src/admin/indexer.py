"""Document parser and background indexer."""

import io
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from config import DOCS_DIR, INDEX_DIR
from src.chat.engine import invalidate_engine


async def save_uploaded_file(file: UploadFile, docs_dir: Path = DOCS_DIR) -> Path:
    dest = docs_dir / file.filename
    content = await file.read()
    dest.write_bytes(content)
    return dest


async def run_indexing(db: AsyncSession) -> None:
    """Delete index, rebuild from docs/, invalidate chat engine."""
    from src.models.system_settings import SystemSettings
    from sqlalchemy import select

    async def _set(key: str, value: str):
        result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
            row.updated_at = datetime.now(timezone.utc)
        else:
            db.add(SystemSettings(key=key, value=value, updated_at=datetime.now(timezone.utc)))
        await db.commit()

    await _set("indexing_status", "running")
    await _set("indexing_started_at", datetime.now(timezone.utc).isoformat())
    await _set("indexing_last_error", "")

    try:
        if INDEX_DIR.exists():
            shutil.rmtree(INDEX_DIR)

        # Import and run the existing indexing pipeline
        from rag_vsnt_offline import build_settings, load_or_build_index
        import rag_vsnt_offline as rag

        from src.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as s2:
            result = await s2.execute(
                select(SystemSettings).where(SystemSettings.key == "ollama_model")
            )
            row = result.scalar_one_or_none()
            rag.OLLAMA_MODEL = row.value if row else "llama3"

        build_settings()
        load_or_build_index()
        invalidate_engine()

        await _set("indexing_status", "idle")
        await _set("indexing_last_completed_at", datetime.now(timezone.utc).isoformat())
    except Exception as exc:
        await _set("indexing_status", "error")
        await _set("indexing_last_error", str(exc))
        raise
