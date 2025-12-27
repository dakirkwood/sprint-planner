# app/core/redis.py
"""
Redis connection factory for ARQ task queue and pub/sub messaging.
"""
from typing import Optional
from arq.connections import RedisSettings, ArqRedis, create_pool

from app.core.config import settings


def get_redis_settings() -> RedisSettings:
    """
    Create Redis settings for ARQ from application config.

    Returns:
        RedisSettings: Configuration for ARQ Redis connection
    """
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        database=settings.REDIS_DB,
    )


async def create_arq_pool() -> ArqRedis:
    """
    Create an ARQ Redis connection pool.

    Returns:
        ArqRedis: Redis connection pool for ARQ operations
    """
    redis_settings = get_redis_settings()
    return await create_pool(redis_settings)


# Global pool reference (set during app lifespan)
_arq_pool: Optional[ArqRedis] = None


async def get_arq_pool() -> ArqRedis:
    """
    Get the global ARQ pool instance.

    Returns:
        ArqRedis: The global Redis pool

    Raises:
        RuntimeError: If pool hasn't been initialized
    """
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_arq_pool()
    return _arq_pool


async def close_arq_pool() -> None:
    """Close the global ARQ pool. Used in application shutdown."""
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.close()
        _arq_pool = None
