"""Audit event logger — writes to the AuditEvent table."""

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_event import AuditEvent


async def log_event(
    db: AsyncSession,
    event_type: str,
    user_id: int | None,
    username_snapshot: str,
    payload: dict,
) -> None:
    event = AuditEvent(
        event_type=event_type,
        user_id=user_id,
        username_snapshot=username_snapshot,
        payload=json.dumps(payload, ensure_ascii=False),
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.commit()


async def log_auth_event(
    db: AsyncSession,
    event_type: str,
    user_id: int | None,
    username: str,
    **payload_kwargs,
) -> None:
    await log_event(db, event_type, user_id, username, dict(payload_kwargs))


async def log_query(
    db: AsyncSession,
    user_id: int,
    username: str,
    question: str,
    answer: str,
    sources: list[str],
    model: str,
) -> None:
    await log_event(
        db,
        "query",
        user_id,
        username,
        {"question": question, "answer": answer[:500], "sources": sources, "model": model},
    )
