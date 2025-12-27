# app/core/database.py
"""
Async database connection setup using SQLAlchemy 2.0 with asyncpg driver.
Provides async session factory and dependency for FastAPI.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


def create_engine(database_url: str | None = None, **kwargs) -> AsyncEngine:
    """
    Create an async SQLAlchemy engine.

    Args:
        database_url: Optional database URL override
        **kwargs: Additional engine configuration

    Returns:
        AsyncEngine instance
    """
    url = database_url or settings.DATABASE_URL

    engine_kwargs = {
        "echo": settings.APP_DEBUG_MODE,
        "pool_pre_ping": True,
    }

    # Use NullPool for SQLite (including aiosqlite)
    if "sqlite" in url:
        engine_kwargs["poolclass"] = NullPool

    engine_kwargs.update(kwargs)

    return create_async_engine(url, **engine_kwargs)


# Default engine instance
engine = create_engine()


# Session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.

    Yields:
        AsyncSession: Database session for the request
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables. Used in application startup."""
    from app.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections. Used in application shutdown."""
    await engine.dispose()
