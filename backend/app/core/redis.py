"""Redis connection factory for ARQ and pub/sub."""

from urllib.parse import urlparse
from typing import Optional

from arq.connections import RedisSettings, ArqRedis, create_pool

from app.core.config import settings


def get_redis_settings() -> RedisSettings:
    """Parse REDIS_URL into ARQ RedisSettings."""
    parsed = urlparse(settings.REDIS_URL)

    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


_arq_pool: Optional[ArqRedis] = None


async def create_arq_pool() -> ArqRedis:
    """Create ARQ connection pool."""
    return await create_pool(get_redis_settings())


async def get_arq_pool() -> ArqRedis:
    """Get or create ARQ connection pool (singleton)."""
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_arq_pool()
    return _arq_pool


async def close_arq_pool() -> None:
    """Close ARQ connection pool."""
    global _arq_pool
    if _arq_pool:
        await _arq_pool.close()
        _arq_pool = None
