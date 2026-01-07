"""Cache helper functions for get/set/delete operations."""
from __future__ import annotations

import asyncio
import logging
from typing import TypeVar, Type, Callable, Awaitable
from pydantic import BaseModel
from app.cache.redis_client import get_redis, is_cache_enabled

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Lock timeout for cache stampede prevention
LOCK_TIMEOUT_SECONDS = 5
LOCK_RETRY_DELAY_SECONDS = 0.1
MAX_LOCK_RETRIES = 50  # 5 seconds total


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
        logger.warning(f"Cache get error for {key}: {e}")

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
        logger.warning(f"Cache set error for {key}: {e}")


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
        logger.warning(f"Cache delete error for {key}: {e}")


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
        logger.warning(f"Cache delete pattern error for {pattern}: {e}")


async def cache_get_or_compute(
    key: str,
    model: Type[T],
    ttl: int,
    compute_func: Callable[[], Awaitable[T]],
) -> T:
    """
    Get cached value or compute it with cache stampede prevention.

    Uses a distributed lock to ensure only one caller computes the value
    when cache is empty or expired. Other callers wait for the result.

    Args:
        key: Cache key
        model: Pydantic model type for deserialization
        ttl: TTL in seconds for cached value
        compute_func: Async function that computes the value if not cached

    Returns:
        Cached or computed value
    """
    # Try to get from cache first
    cached = await cache_get(key, model)
    if cached is not None:
        return cached

    redis = get_redis()
    if not redis or not is_cache_enabled():
        # Cache disabled, just compute
        return await compute_func()

    lock_key = f"lock:{key}"

    # Try to acquire lock
    try:
        acquired = await redis.set(lock_key, "1", nx=True, ex=LOCK_TIMEOUT_SECONDS)
    except Exception as e:
        logger.warning(f"Failed to acquire lock for {key}: {e}")
        # Fall back to computing without lock
        return await compute_func()

    if acquired:
        # We got the lock, compute and cache the value
        try:
            result = await compute_func()
            await cache_set(key, result, ttl)
            return result
        finally:
            # Release lock
            try:
                await redis.delete(lock_key)
            except Exception:
                pass
    else:
        # Someone else is computing, wait and retry
        for _ in range(MAX_LOCK_RETRIES):
            await asyncio.sleep(LOCK_RETRY_DELAY_SECONDS)

            # Check if value is now in cache
            cached = await cache_get(key, model)
            if cached is not None:
                return cached

            # Check if lock is still held
            try:
                lock_exists = await redis.exists(lock_key)
                if not lock_exists:
                    # Lock was released but value not in cache, try to acquire
                    acquired = await redis.set(lock_key, "1", nx=True, ex=LOCK_TIMEOUT_SECONDS)
                    if acquired:
                        try:
                            result = await compute_func()
                            await cache_set(key, result, ttl)
                            return result
                        finally:
                            try:
                                await redis.delete(lock_key)
                            except Exception:
                                pass
            except Exception:
                pass

        # Timeout waiting for lock, compute anyway
        logger.warning(f"Timeout waiting for cache lock on {key}, computing directly")
        return await compute_func()
