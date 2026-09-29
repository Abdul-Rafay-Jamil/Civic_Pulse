"""FastAPI dependency injection — database sessions, triage provider."""

from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.factory import create_triage_provider

# ── Database engine (async) ─────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Triage provider (singleton) ─────────────────────────────────────────
_triage_provider: TriageProvider | None = None


def get_triage_provider() -> TriageProvider:
    """Return the singleton triage provider."""
    global _triage_provider
    if _triage_provider is None:
        _triage_provider = create_triage_provider()
    return _triage_provider


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session — auto-closed after request."""
    async with async_session_factory() as session:
        yield session


async def check_db_health() -> bool:
    """Check if the database is reachable. Used by /ready."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception:
        return False


async def close_db_engine() -> None:
    """Dispose the engine during shutdown."""
    await engine.dispose()
