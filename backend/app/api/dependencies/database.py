"""Database session dependency."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for request.

    Yields:
        AsyncSession: Database session that auto-commits on success
                     and rolls back on exception.
    """
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
