"""Redis client for caching."""
from __future__ import annotations

import redis.asyncio as redis
from app.core.config import get_settings

redis_client: redis.Redis | None = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    settings = get_settings()

    if not settings.redis_url:
        print("Redis URL not configured, caching disabled")
        return

    try:
        redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await redis_client.ping()
        print("Redis connected successfully")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")
        redis_client = None


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        print("Redis connection closed")


def get_redis() -> redis.Redis | None:
    """Get Redis client instance. Returns None if not initialized."""
    return redis_client


def is_cache_enabled() -> bool:
    """Check if caching is enabled and Redis is connected."""
    return redis_client is not None
