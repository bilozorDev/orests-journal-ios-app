"""
Tests for rate limiting functionality.

Tests cover:
- rate_limit decorator skipping in debug mode
- Rate limit allowing requests under limit
- Rate limit graceful degradation when Redis unavailable
- Integration test with FastAPI endpoint
"""
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from httpx import ASGITransport, AsyncClient

from app.core.rate_limit import rate_limit


def create_mock_request(ip: str = "192.168.1.100", forwarded_ip: str = None):
    """Create a mock Request object."""
    mock_request = MagicMock(spec=Request)

    # Create a real dict for headers
    headers = {}
    if forwarded_ip:
        headers["X-Forwarded-For"] = forwarded_ip
    mock_request.headers = headers

    # Mock client
    mock_client = MagicMock()
    mock_client.host = ip
    mock_request.client = mock_client

    return mock_request


class TestRateLimitDecorator:
    """Tests for the @rate_limit decorator."""

    @pytest.mark.asyncio
    async def test_rate_limit_skipped_in_debug_mode(self):
        """
        Should skip rate limiting when DEBUG=true.
        This test passes because DEBUG=true is set in conftest.py.
        """
        call_count = 0

        @rate_limit(requests=1, window_seconds=60)
        async def test_func(request: Request):
            nonlocal call_count
            call_count += 1
            return {"success": True}

        mock_request = create_mock_request()

        # DEBUG=true is set in conftest.py, so rate limiting is skipped
        # Should succeed even with 5 calls when limit is 1
        for _ in range(5):
            result = await test_func(request=mock_request)
            assert result == {"success": True}

        assert call_count == 5

    @pytest.mark.asyncio
    async def test_rate_limit_allows_requests_under_limit(self):
        """
        Should allow requests when under rate limit.
        In debug mode, requests always pass through.
        """
        call_count = 0

        @rate_limit(requests=5, window_seconds=60)
        async def test_func(request: Request):
            nonlocal call_count
            call_count += 1
            return {"success": True}

        mock_request = create_mock_request()

        # Make 3 requests (under any limit)
        for _ in range(3):
            result = await test_func(request=mock_request)
            assert result == {"success": True}

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_passes_without_redis(self):
        """Should pass requests through when Redis is unavailable."""
        call_count = 0

        @rate_limit(requests=1, window_seconds=60)
        async def test_func(request: Request):
            nonlocal call_count
            call_count += 1
            return {"success": True}

        mock_request = create_mock_request()

        # Even if Redis was checked, it would be unavailable
        with patch("app.core.rate_limit.get_redis", return_value=None):
            # Should succeed even with many calls when Redis is unavailable
            for _ in range(10):
                result = await test_func(request=mock_request)
                assert result == {"success": True}

            assert call_count == 10


class TestRateLimitIntegration:
    """Integration tests for rate limiting with FastAPI."""

    @pytest.fixture
    def rate_limited_app(self):
        """Create a test app with rate-limited endpoint."""
        app = FastAPI()

        @app.post("/test-endpoint")
        @rate_limit(requests=3, window_seconds=60)
        async def test_endpoint(request: Request):
            return {"message": "success"}

        return app

    @pytest.fixture
    async def test_client(self, rate_limited_app):
        """Create async client for rate-limited app."""
        transport = ASGITransport(app=rate_limited_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_after_limit_when_not_debug(
        self,
        test_client: AsyncClient,
    ):
        """
        Should block requests after rate limit in integration test.
        Uses mocked os module to simulate non-debug mode.
        """
        call_count = 0

        async def mock_zcard(*args):
            nonlocal call_count
            call_count += 1
            return call_count

        mock_redis = AsyncMock()
        mock_redis.zremrangebyscore = AsyncMock()
        mock_redis.zadd = AsyncMock()
        mock_redis.zcard = mock_zcard
        mock_redis.expire = AsyncMock()

        # Mock os module to return DEBUG=false
        mock_os = MagicMock()
        mock_os.getenv = lambda k, d="": "false" if k == "DEBUG" else os.environ.get(k, d)

        with patch.object(__import__("app.core.rate_limit", fromlist=[""]), "os", mock_os):
            with patch("app.core.rate_limit.get_redis", return_value=mock_redis):
                # First 3 requests should succeed
                for i in range(3):
                    response = await test_client.post("/test-endpoint")
                    assert response.status_code == 200, f"Request {i+1} failed unexpectedly"

                # 4th request should be rate limited
                response = await test_client.post("/test-endpoint")
                assert response.status_code == 429
                assert "Retry-After" in response.headers

    @pytest.mark.asyncio
    async def test_rate_limit_endpoint_returns_200_in_debug_mode(
        self,
        test_client: AsyncClient,
    ):
        """
        In debug mode, all requests should succeed regardless of count.
        """
        # Make 10 requests - all should succeed in debug mode
        for i in range(10):
            response = await test_client.post("/test-endpoint")
            assert response.status_code == 200, f"Request {i+1} failed unexpectedly"
