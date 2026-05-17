"""Admin user management routes."""

import secrets
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import TEMPLATES_DIR
from src.db.database import get_db
from src.models.user import User
from src.models.audit_event import USER_CREATED, USER_DEACTIVATED, USER_REACTIVATED, USER_DELETED
from src.auth.service import create_user, count_active_admins, require_admin
from src.audit.logger import log_auth_event

router = APIRouter(prefix="/admin/users")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def users_list(request: Request, db: AsyncSession = Depends(get_db)):
    require_admin(request)
    result = await db.execute(select(User).order_by(User.created_at))
    users = result.scalars().all()
    return templates.TemplateResponse(request, "admin/users.html", {
        "current_user": request.state.current_user,
        "messages": [],
        "users": users,
        "temp_password": request.query_params.get("temp_password"),
        "new_username": request.query_params.get("new_username"),
    })


@router.post("", response_class=HTMLResponse)
async def users_create(
    request: Request,
    username: str = Form(...),
    role: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)
    admin = request.state.current_user

    username = username.strip().lower()
    if role not in ("admin", "operator"):
        raise HTTPException(status_code=400, detail="Papel inválido.")

    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none():
        result = await db.execute(select(User).order_by(User.created_at))
        users = result.scalars().all()
        return templates.TemplateResponse(request, "admin/users.html", {
            "current_user": admin,
            "messages": [("error", f"Usuário '{username}' já existe.")],
            "users": users, "temp_password": None, "new_username": None,
        })

    temp_pw = secrets.token_urlsafe(12)
    user = await create_user(db, username, temp_pw, role=role)
    await log_auth_event(db, USER_CREATED, admin.id, admin.username,
                         target_username=user.username, role=role)

    return RedirectResponse(
        f"/admin/users?temp_password={temp_pw}&new_username={user.username}",
        status_code=302,
    )


@router.post("/{user_id}/toggle-active")
async def users_toggle_active(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)
    admin = request.state.current_user

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if user.is_active and user.role == "admin" and await count_active_admins(db) <= 1:
        raise HTTPException(status_code=400, detail="Não é possível desativar o único administrador ativo.")

    user.is_active = not user.is_active
    await db.commit()

    event = USER_REACTIVATED if user.is_active else USER_DEACTIVATED
    await log_auth_event(db, event, admin.id, admin.username, target_username=user.username)

    return RedirectResponse("/admin/users", status_code=302)


@router.post("/{user_id}/delete")
async def users_delete(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_admin(request)
    admin = request.state.current_user

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if user.role == "admin" and await count_active_admins(db) <= 1:
        raise HTTPException(status_code=400, detail="Não é possível excluir o único administrador.")

    username_snap = user.username
    await db.delete(user)
    await db.commit()
    await log_auth_event(db, USER_DELETED, admin.id, admin.username, target_username=username_snap)

    return RedirectResponse("/admin/users", status_code=302)
