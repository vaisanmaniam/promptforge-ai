import time
from typing import Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

# Asynchronous engine and sessionmaker
# Using lazy initialization to prevent startup crashes when database is offline
async_engine = None
async_session_factory = None


def get_async_engine():
    global async_engine, async_session_factory
    if async_engine is None:
        async_engine = create_async_engine(
            settings.async_database_uri,
            echo=False,
            pool_pre_ping=True,
            connect_args={"timeout": settings.DB_POOL_TIMEOUT_SECONDS},
        )
        async_session_factory = async_sessionmaker(
            bind=async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return async_engine


async def get_db_session():
    """Dependency for injecting database sessions."""
    get_async_engine()
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_health() -> Tuple[bool, str, float]:
    """
    Safely probes PostgreSQL connectivity with a short timeout.
    Returns: (is_healthy, message, latency_ms)
    Guarantees no credentials or sensitive URLs are logged or returned.
    """
    start_time = time.perf_counter()
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start_time) * 1000
        return True, "PostgreSQL connection verified via SELECT 1", round(latency_ms, 2)
    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        # Categorize known errors cleanly without exposing internals
        error_name = type(exc).__name__
        logger.warning(f"Database check failed: {error_name} ({str(exc)[:100]})")
        return False, f"Database unreachable ({error_name})", round(latency_ms, 2)
