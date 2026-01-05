"""Rate limiting middleware for API endpoints."""
import os
import time
import logging
from typing import Callable, Optional
from collections import defaultdict
from functools import wraps

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.cache.redis_client import get_redis

logger = logging.getLogger(__name__)


# In-memory fallback when Redis is not available
_memory_store: dict[str, list[float]] = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using sliding window algorithm.

    Limits requests per IP address with optional endpoint-specific limits.
    Falls back to in-memory storage when Redis is unavailable.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_limit: int = 10,  # Max requests in a 1-second window
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.window_seconds = 60

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting in test/debug mode
        if os.getenv("DEBUG", "").lower() == "true":
            return await call_next(request)

        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get client identifier (prefer X-Forwarded-For for proxied requests)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else "unknown"

        # Rate limit key
        key = f"rate_limit:{client_ip}"

        try:
            is_allowed, remaining = await self._check_rate_limit(key)
        except Exception as e:
            # On error, allow request but log warning
            logger.warning(f"Rate limit check failed: {e}")
            is_allowed = True
            remaining = -1

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)

        # Add rate limit headers
        if remaining >= 0:
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    async def _check_rate_limit(self, key: str) -> tuple[bool, int]:
        """Check if request is allowed under rate limit.

        Returns (is_allowed, remaining_requests)
        """
        redis = get_redis()
        now = time.time()
        window_start = now - self.window_seconds

        if redis:
            return await self._check_rate_limit_redis(redis, key, now, window_start)
        else:
            return self._check_rate_limit_memory(key, now, window_start)

    async def _check_rate_limit_redis(
        self, redis, key: str, now: float, window_start: float
    ) -> tuple[bool, int]:
        """Redis-based rate limiting using sorted sets."""
        pipe = redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Count requests in window
        pipe.zcard(key)
        # Set expiry on key
        pipe.expire(key, self.window_seconds + 10)

        results = await pipe.execute()
        request_count = results[2]

        remaining = max(0, self.requests_per_minute - request_count)
        is_allowed = request_count <= self.requests_per_minute

        return is_allowed, remaining

    def _check_rate_limit_memory(
        self, key: str, now: float, window_start: float
    ) -> tuple[bool, int]:
        """In-memory fallback rate limiting."""
        # Clean old entries
        _memory_store[key] = [t for t in _memory_store[key] if t > window_start]

        # Add current request
        _memory_store[key].append(now)

        request_count = len(_memory_store[key])
        remaining = max(0, self.requests_per_minute - request_count)
        is_allowed = request_count <= self.requests_per_minute

        return is_allowed, remaining


def rate_limit(
    requests: int = 10,
    window_seconds: int = 60,
    key_func: Optional[Callable[[Request], str]] = None,
):
    """
    Decorator for endpoint-specific rate limiting.

    Usage:
        @router.post("/login")
        @rate_limit(requests=5, window_seconds=60)
        async def login(...):
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Skip rate limiting in test/debug mode
            if os.getenv("DEBUG", "").lower() == "true":
                return await func(*args, **kwargs)

            # Find request in args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            if request:
                client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                if not client_ip:
                    client_ip = request.client.host if request.client else "unknown"

                if key_func:
                    key = f"endpoint_limit:{func.__name__}:{key_func(request)}"
                else:
                    key = f"endpoint_limit:{func.__name__}:{client_ip}"

                redis = get_redis()
                now = time.time()
                window_start = now - window_seconds

                if redis:
                    await redis.zremrangebyscore(key, 0, window_start)
                    await redis.zadd(key, {str(now): now})
                    count = await redis.zcard(key)
                    await redis.expire(key, window_seconds + 10)

                    if count > requests:
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many requests for this endpoint.",
                            headers={"Retry-After": str(window_seconds)},
                        )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
