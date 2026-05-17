"""Async SQLAlchemy engine and session factory."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from config import DB_PATH


class Base(DeclarativeBase):
    pass


DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DB_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Create tables, enable WAL mode and foreign key enforcement."""
    async with engine.begin() as conn:
        from src.models import Base as ModelsBase  # noqa: import triggers model registration
        await conn.run_sync(ModelsBase.metadata.create_all)
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))


async def get_db():
    """FastAPI dependency that yields an AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session
