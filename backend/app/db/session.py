"""Async SQLAlchemy engine/session lifecycle."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base


def _ensure_sqlite_directory(url: str) -> None:
    if not url.startswith("sqlite+aiosqlite:///"):
        return
    raw_path = url.removeprefix("sqlite+aiosqlite:///")
    db_path = Path(raw_path).expanduser()
    if db_path.parent and str(db_path.parent) != "":
        db_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(settings.database_url)
_engine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)
_session_factory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Provide an async DB session."""
    async with _session_factory() as session:
        yield session


async def init_database() -> None:
    """Ensure DB schema exists for runtime usage."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database() -> None:
    """Dispose DB engine cleanly."""
    await _engine.dispose()

