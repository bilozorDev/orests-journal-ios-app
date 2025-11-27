"""Cache helper functions for get/set/delete operations."""
from __future__ import annotations

from typing import TypeVar, Type
from pydantic import BaseModel
from app.cache.redis_client import get_redis, is_cache_enabled

T = TypeVar("T", bound=BaseModel)


async def cache_get(key: str, model: Type[T]) -> T | None:
    """
    Get cached value and deserialize to Pydantic model.
    Returns None if cache is disabled, key doesn't exist, or deserialization fails.
    """
    if not is_cache_enabled():
        return None

    redis = get_redis()
    if not redis:
        return None

    try:
        data = await redis.get(key)
        if data:
            return model.model_validate_json(data)
    except Exception as e:
        print(f"Cache get error for {key}: {e}")

    return None


async def cache_set(key: str, value: BaseModel, ttl: int) -> None:
    """
    Serialize Pydantic model and cache with TTL.
    Silently fails if cache is disabled.
    """
    if not is_cache_enabled():
        return

    redis = get_redis()
    if not redis:
        return

    try:
        await redis.setex(key, ttl, value.model_dump_json())
    except Exception as e:
        print(f"Cache set error for {key}: {e}")


async def cache_delete(key: str) -> None:
    """
    Delete a cache key.
    Silently fails if cache is disabled.
    """
    if not is_cache_enabled():
        return

    redis = get_redis()
    if not redis:
        return

    try:
        await redis.delete(key)
    except Exception as e:
        print(f"Cache delete error for {key}: {e}")


async def cache_delete_pattern(pattern: str) -> None:
    """
    Delete all keys matching pattern (use sparingly).
    Silently fails if cache is disabled.
    """
    if not is_cache_enabled():
        return

    redis = get_redis()
    if not redis:
        return

    try:
        keys = []
        async for key in redis.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            await redis.delete(*keys)
    except Exception as e:
        print(f"Cache delete pattern error for {pattern}: {e}")
