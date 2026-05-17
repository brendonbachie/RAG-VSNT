"""Admin settings routes — model selection and session timeout."""

import json
import urllib.request
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import OLLAMA_URL, TEMPLATES_DIR
from src.db.database import get_db
from src.models.system_settings import SystemSettings
from src.models.audit_event import MODEL_CHANGED, SETTINGS_CHANGED
from src.auth.service import require_admin
from src.audit.logger import log_auth_event
from src.chat.engine import invalidate_engine

router = APIRouter(prefix="/admin/settings")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _fetch_ollama_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=3) as r:
            data = json.loads(r.read())
        return [m["name"].split(":")[0] for m in data.get("models", [])]
    except Exception:
        return []


async def _get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def _upsert(db: AsyncSession, key: str, value: str, user_id: int | None = None):
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    row = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if row:
        row.value = value
        row.updated_at = now
        row.updated_by_user_id = user_id
    else:
        db.add(SystemSettings(key=key, value=value, updated_at=now, updated_by_user_id=user_id))
    await db.commit()


@router.get("", response_class=HTMLResponse)
async def settings_get(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    current_model = await _get_setting(db, "ollama_model", "llama3")
    current_timeout = await _get_setting(db, "session_timeout_seconds", "28800")
    available_models = _fetch_ollama_models()

    return templates.TemplateResponse(request, "admin/settings.html", {
        "current_user": request.state.current_user,
        "messages": [],
        "current_model": current_model,
        "current_timeout": current_timeout,
        "available_models": available_models,
    })


@router.post("")
async def settings_post(
    request: Request,
    ollama_model: str = Form(...),
    session_timeout_seconds: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)
    admin = request.state.current_user

    available = _fetch_ollama_models()
    if available and ollama_model not in available:
        raise HTTPException(
            status_code=400,
            detail=f"Modelo '{ollama_model}' não está instalado no Ollama. "
                   f"Disponíveis: {', '.join(available)}"
        )

    if not (60 <= session_timeout_seconds <= 86400):
        raise HTTPException(status_code=400, detail="Timeout deve estar entre 60 e 86400 segundos.")

    old_model = await _get_setting(db, "ollama_model", "llama3")
    old_timeout = await _get_setting(db, "session_timeout_seconds", "28800")

    if ollama_model != old_model:
        await _upsert(db, "ollama_model", ollama_model, admin.id)
        await log_auth_event(db, MODEL_CHANGED, admin.id, admin.username,
                             **{"from": old_model, "to": ollama_model})
        invalidate_engine()

    if str(session_timeout_seconds) != old_timeout:
        await _upsert(db, "session_timeout_seconds", str(session_timeout_seconds), admin.id)
        await log_auth_event(db, SETTINGS_CHANGED, admin.id, admin.username,
                             key="session_timeout_seconds",
                             old=old_timeout, new=str(session_timeout_seconds))

    return RedirectResponse("/admin/settings?saved=1", status_code=302)
