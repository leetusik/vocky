"""Database engine and session helpers."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from vocky.config import get_settings

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the shared async engine."""

    global _engine

    if _engine is None:
        _engine = create_async_engine(
            get_settings().database_url,
            pool_pre_ping=True,
        )

    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the shared async sessionmaker."""

    global _session_maker

    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
        )

    return _session_maker


async def dispose_engine() -> None:
    """Dispose the cached engine during app shutdown."""

    global _engine, _session_maker

    if _engine is not None:
        await _engine.dispose()

    _engine = None
    _session_maker = None
