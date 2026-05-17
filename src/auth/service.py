"""Auth service — user CRUD, password verification, FastAPI dependencies."""

from fastapi import Request, HTTPException
from passlib.context import CryptContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.auth.session import get_session_data

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


async def create_user(db: AsyncSession, username: str, password: str, role: str) -> User:
    user = User(
        username=username.lower(),
        password_hash=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(
        select(User).where(func.lower(User.username) == username.lower())
    )
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def count_active_admins(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count()).where(User.role == "admin", User.is_active == True)
    )
    return result.scalar_one()


def require_auth(request: Request) -> User:
    """FastAPI dependency — returns current user or raises 401 redirect."""
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


def require_admin(request: Request) -> User:
    """FastAPI dependency — returns current admin user or raises 403."""
    user = require_auth(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    return user
