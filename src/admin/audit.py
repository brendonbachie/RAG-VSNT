"""Admin audit log routes."""

import json
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import TEMPLATES_DIR
from src.db.database import get_db
from src.models.audit_event import AuditEvent
from src.auth.service import require_admin

router = APIRouter(prefix="/admin/audit")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def audit_list(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(
        select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100)
    )
    events = result.scalars().all()

    def _summary(payload_str: str) -> str:
        try:
            d = json.loads(payload_str)
            if "question" in d:
                return d["question"][:80]
            if "target_username" in d:
                return f"→ {d['target_username']}"
            if "filename" in d:
                return d["filename"]
            if "to" in d:
                return f"{d.get('from','')} → {d['to']}"
            return ""
        except Exception:
            return payload_str[:80]

    return templates.TemplateResponse(request, "admin/audit.html", {
        "current_user": request.state.current_user,
        "messages": [],
        "events": events,
        "summary": _summary,
    })


@router.get("/api")
async def audit_api(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    event_type: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)

    query = select(AuditEvent).order_by(AuditEvent.created_at.desc())
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)

    total_result = await db.execute(select(func.count()).select_from(AuditEvent))
    total = total_result.scalar_one()

    result = await db.execute(query.offset(offset).limit(limit))
    events = result.scalars().all()

    return JSONResponse({
        "total": total,
        "events": [
            {
                "id": e.id,
                "created_at": e.created_at.isoformat(),
                "event_type": e.event_type,
                "username": e.username_snapshot,
                "payload": json.loads(e.payload),
            }
            for e in events
        ],
    })
