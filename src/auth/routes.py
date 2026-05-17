"""Auth routes: /setup, /login, /logout."""

from datetime import datetime, timezone

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from config import TEMPLATES_DIR
from src.db.database import get_db, AsyncSessionLocal
from src.models.system_settings import SystemSettings
from src.models.audit_event import LOGIN_SUCCESS, LOGIN_FAILURE, LOGOUT, USER_CREATED
from src.auth.service import (
    create_user, get_user_by_username, verify_password,
)
from src.auth.session import set_session_cookie, clear_session_cookie, get_session_data
from src.audit.logger import log_auth_event
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def _get_setting(db: AsyncSession, key: str) -> str:
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else ""


async def _set_setting(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
        row.updated_at = datetime.now(timezone.utc)
    else:
        db.add(SystemSettings(key=key, value=value, updated_at=datetime.now(timezone.utc)))
    await db.commit()


# ── Setup wizard ──────────────────────────────────────────────────────────────

@router.get("/setup", response_class=HTMLResponse)
async def setup_get(request: Request, db: AsyncSession = Depends(get_db)):
    if await _get_setting(db, "setup_complete") == "true":
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("setup.html", {
        "request": request, "current_user": None, "messages": [], "error": None, "username": ""
    })


@router.post("/setup", response_class=HTMLResponse)
async def setup_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if await _get_setting(db, "setup_complete") == "true":
        return RedirectResponse("/login", status_code=302)

    username = username.strip()
    if not username or not password:
        return templates.TemplateResponse("setup.html", {
            "request": request, "current_user": None, "messages": [],
            "error": "Usuário e senha são obrigatórios.", "username": username,
        })

    import re
    if not re.match(r"^[a-zA-Z0-9_\-]{1,64}$", username):
        return templates.TemplateResponse("setup.html", {
            "request": request, "current_user": None, "messages": [],
            "error": "Nome de usuário inválido. Use apenas letras, números, _ e -.", "username": username,
        })

    user = await create_user(db, username, password, role="admin")
    await _set_setting(db, "setup_complete", "true")
    await log_auth_event(db, USER_CREATED, user.id, user.username, role="admin", target_username=user.username)

    response = RedirectResponse("/", status_code=302)
    set_session_cookie(response, {"user_id": user.id, "username": user.username, "role": user.role})
    return response


# ── Login ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    if get_session_data(request):
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request, "current_user": None, "messages": [], "error": None
    })


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    async with AsyncSessionLocal() as db2:
        from src.models.system_settings import DEFAULTS
        result = await db2.execute(select(SystemSettings).where(SystemSettings.key == "session_timeout_seconds"))
        row = result.scalar_one_or_none()
        timeout = int(row.value) if row else 28800

    user = await get_user_by_username(db, username)

    if user is None:
        await log_auth_event(db, LOGIN_FAILURE, None, username, reason="user_not_found")
        return templates.TemplateResponse("login.html", {
            "request": request, "current_user": None, "messages": [],
            "error": "Usuário ou senha inválidos."
        })

    if not user.is_active:
        await log_auth_event(db, LOGIN_FAILURE, user.id, user.username, reason="user_inactive")
        return templates.TemplateResponse("login.html", {
            "request": request, "current_user": None, "messages": [],
            "error": "Usuário ou senha inválidos."
        })

    if not verify_password(password, user.password_hash):
        await log_auth_event(db, LOGIN_FAILURE, user.id, user.username, reason="bad_password")
        return templates.TemplateResponse("login.html", {
            "request": request, "current_user": None, "messages": [],
            "error": "Usuário ou senha inválidos."
        })

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    await log_auth_event(db, LOGIN_SUCCESS, user.id, user.username)

    response = RedirectResponse("/", status_code=302)
    set_session_cookie(response, {"user_id": user.id, "username": user.username, "role": user.role}, timeout=timeout)
    return response


# ── Logout ────────────────────────────────────────────────────────────────────

@router.get("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    user = getattr(request.state, "current_user", None)
    if user:
        await log_auth_event(db, LOGOUT, user.id, user.username)
    response = RedirectResponse("/login", status_code=302)
    clear_session_cookie(response)
    return response
