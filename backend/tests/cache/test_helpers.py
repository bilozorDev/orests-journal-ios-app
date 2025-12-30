"""
Unit tests for cache helper functions.

Tests cache_get, cache_set, cache_delete, and cache_delete_pattern functions
with various scenarios including Redis availability, data serialization, and error handling.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.cache.helpers import (
    cache_delete,
    cache_delete_pattern,
    cache_get,
    cache_set,
)


# Test Pydantic models for serialization testing
class SimpleModel(BaseModel):
    """Simple test model."""
    id: str
    name: str


class ComplexModel(BaseModel):
    """Complex test model with nested fields."""
    id: str
    name: str
    count: int
    tags: list[str]
    metadata: dict[str, str]


class TestCacheGet:
    """Tests for cache_get function."""

    @pytest.mark.asyncio
    async def test_cache_get_success(self):
        """Should deserialize cached JSON data to Pydantic model."""
        test_id = str(uuid4())
        cached_json = f'{{"id": "{test_id}", "name": "Test"}}'

        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_json

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get("test:key", SimpleModel)

        assert result is not None
        assert result.id == test_id
        assert result.name == "Test"
        mock_redis.get.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_cache_get_complex_model(self):
        """Should deserialize complex nested Pydantic model."""
        test_id = str(uuid4())
        cached_json = f'''{{
            "id": "{test_id}",
            "name": "Complex",
            "count": 42,
            "tags": ["tag1", "tag2"],
            "metadata": {{"key": "value"}}
        }}'''

        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_json

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get("test:key", ComplexModel)

        assert result is not None
        assert result.id == test_id
        assert result.name == "Complex"
        assert result.count == 42
        assert result.tags == ["tag1", "tag2"]
        assert result.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_cache_get_key_not_found(self):
        """Should return None when key doesn't exist in cache."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get("nonexistent:key", SimpleModel)

        assert result is None
        mock_redis.get.assert_called_once_with("nonexistent:key")

    @pytest.mark.asyncio
    async def test_cache_get_cache_disabled(self):
        """Should return None when cache is disabled."""
        with patch("app.cache.helpers.is_cache_enabled", return_value=False):
            result = await cache_get("test:key", SimpleModel)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_redis_not_available(self):
        """Should return None when Redis client is not available."""
        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=None):
            result = await cache_get("test:key", SimpleModel)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_invalid_json(self):
        """Should return None and log error when cached data is invalid JSON."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "invalid json {{"

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get("test:key", SimpleModel)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_validation_error(self):
        """Should return None when JSON doesn't match Pydantic model schema."""
        # Missing required 'name' field
        cached_json = f'{{"id": "{uuid4()}"}}'

        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_json

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get("test:key", SimpleModel)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_redis_connection_error(self):
        """Should return None when Redis get() raises exception."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis connection failed")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get("test:key", SimpleModel)

        assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_empty_string(self):
        """Should return None when cached value is empty string."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = ""

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get("test:key", SimpleModel)

        assert result is None


class TestCacheSet:
    """Tests for cache_set function."""

    @pytest.mark.asyncio
    async def test_cache_set_success(self):
        """Should serialize Pydantic model to JSON and cache with TTL."""
        model = SimpleModel(id=str(uuid4()), name="Test")

        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_set("test:key", model, ttl=300)

        # Verify setex was called with correct arguments
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]

        assert call_args[0] == "test:key"
        assert call_args[1] == 300
        # Verify JSON string contains expected data
        assert model.id in call_args[2]
        assert model.name in call_args[2]

    @pytest.mark.asyncio
    async def test_cache_set_complex_model(self):
        """Should serialize complex nested model correctly."""
        model = ComplexModel(
            id=str(uuid4()),
            name="Complex",
            count=42,
            tags=["tag1", "tag2"],
            metadata={"key": "value"}
        )

        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_set("test:key", model, ttl=600)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]

        assert call_args[0] == "test:key"
        assert call_args[1] == 600
        # Verify all fields are in JSON
        json_str = call_args[2]
        assert model.id in json_str
        assert "Complex" in json_str
        assert "42" in json_str
        assert "tag1" in json_str

    @pytest.mark.asyncio
    async def test_cache_set_different_ttls(self):
        """Should respect different TTL values."""
        model = SimpleModel(id=str(uuid4()), name="Test")
        mock_redis = AsyncMock()

        ttls = [60, 300, 3600, 86400]

        for ttl in ttls:
            mock_redis.reset_mock()

            with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
                 patch("app.cache.helpers.get_redis", return_value=mock_redis):
                await cache_set(f"test:key:{ttl}", model, ttl=ttl)

            call_args = mock_redis.setex.call_args[0]
            assert call_args[1] == ttl

    @pytest.mark.asyncio
    async def test_cache_set_cache_disabled(self):
        """Should silently return when cache is disabled."""
        model = SimpleModel(id=str(uuid4()), name="Test")
        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=False):
            await cache_set("test:key", model, ttl=300)

        # Redis should never be called
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_set_redis_not_available(self):
        """Should silently return when Redis client is not available."""
        model = SimpleModel(id=str(uuid4()), name="Test")
        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=None):
            await cache_set("test:key", model, ttl=300)

        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_set_redis_connection_error(self):
        """Should silently fail when Redis setex() raises exception."""
        model = SimpleModel(id=str(uuid4()), name="Test")

        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = ConnectionError("Redis connection failed")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Should not raise exception
            await cache_set("test:key", model, ttl=300)

        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_set_serialization_error(self):
        """Should handle model_dump_json() errors gracefully."""
        model = SimpleModel(id=str(uuid4()), name="Test")

        mock_redis = AsyncMock()

        # Mock the BaseModel.model_dump_json method at the class level
        original_method = BaseModel.model_dump_json

        def mock_dump_json(self, **kwargs):
            raise ValueError("Serialization error")

        with patch.object(BaseModel, "model_dump_json", mock_dump_json), \
             patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Should not raise exception
            await cache_set("test:key", model, ttl=300)

        # setex should not be called due to error
        mock_redis.setex.assert_not_called()


class TestCacheDelete:
    """Tests for cache_delete function."""

    @pytest.mark.asyncio
    async def test_cache_delete_success(self):
        """Should delete key from Redis."""
        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_delete("test:key")

        mock_redis.delete.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_cache_delete_multiple_calls(self):
        """Should delete each key independently."""
        mock_redis = AsyncMock()
        keys = ["key:1", "key:2", "key:3"]

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            for key in keys:
                await cache_delete(key)

        assert mock_redis.delete.call_count == 3
        for i, key in enumerate(keys):
            assert mock_redis.delete.call_args_list[i][0][0] == key

    @pytest.mark.asyncio
    async def test_cache_delete_cache_disabled(self):
        """Should silently return when cache is disabled."""
        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=False):
            await cache_delete("test:key")

        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_delete_redis_not_available(self):
        """Should silently return when Redis client is not available."""
        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=None):
            await cache_delete("test:key")

        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_delete_redis_connection_error(self):
        """Should silently fail when Redis delete() raises exception."""
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = ConnectionError("Redis connection failed")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Should not raise exception
            await cache_delete("test:key")

        mock_redis.delete.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_cache_delete_nonexistent_key(self):
        """Should handle deleting nonexistent key gracefully."""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 0  # Redis returns 0 when key doesn't exist

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_delete("nonexistent:key")

        mock_redis.delete.assert_called_once_with("nonexistent:key")


class TestCacheDeletePattern:
    """Tests for cache_delete_pattern function."""

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_success(self):
        """Should find and delete all keys matching pattern."""
        mock_redis = AsyncMock()

        # Mock scan_iter to yield matching keys
        async def mock_scan_iter(match):
            for key in ["user:1", "user:2", "user:3"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_delete_pattern("user:*")

        # Should delete all found keys
        mock_redis.delete.assert_called_once_with("user:1", "user:2", "user:3")

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_no_matches(self):
        """Should handle case when no keys match pattern."""
        mock_redis = AsyncMock()

        # Mock scan_iter to yield no keys
        async def mock_scan_iter(match):
            return
            yield  # Make it a generator

        mock_redis.scan_iter = mock_scan_iter

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_delete_pattern("nonexistent:*")

        # Should not call delete when no keys found
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_single_match(self):
        """Should delete single key matching pattern."""
        mock_redis = AsyncMock()

        async def mock_scan_iter(match):
            yield "pet:12345"

        mock_redis.scan_iter = mock_scan_iter

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_delete_pattern("pet:*")

        mock_redis.delete.assert_called_once_with("pet:12345")

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_complex_pattern(self):
        """Should work with complex Redis patterns."""
        mock_redis = AsyncMock()

        async def mock_scan_iter(match):
            # Pattern: dashboard:*:2025-01-*
            for key in ["dashboard:pet1:2025-01-15", "dashboard:pet2:2025-01-20"]:
                yield key

        mock_redis.scan_iter = mock_scan_iter

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_delete_pattern("dashboard:*:2025-01-*")

        mock_redis.delete.assert_called_once()
        call_args = mock_redis.delete.call_args[0]
        assert "dashboard:pet1:2025-01-15" in call_args
        assert "dashboard:pet2:2025-01-20" in call_args

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_cache_disabled(self):
        """Should silently return when cache is disabled."""
        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=False):
            await cache_delete_pattern("test:*")

        # scan_iter and delete should never be called
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_redis_not_available(self):
        """Should silently return when Redis client is not available."""
        mock_redis = AsyncMock()

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=None):
            await cache_delete_pattern("test:*")

        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_scan_error(self):
        """Should handle scan_iter() errors gracefully."""
        mock_redis = AsyncMock()

        async def mock_scan_iter(match):
            raise ConnectionError("Redis connection failed during scan")
            yield  # Make it a generator

        mock_redis.scan_iter = mock_scan_iter

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Should not raise exception
            await cache_delete_pattern("test:*")

        # delete should not be called due to scan error
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_delete_error(self):
        """Should handle delete() errors gracefully after successful scan."""
        mock_redis = AsyncMock()

        async def mock_scan_iter(match):
            yield "key:1"
            yield "key:2"

        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete.side_effect = ConnectionError("Redis connection failed during delete")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Should not raise exception
            await cache_delete_pattern("key:*")

        # delete should have been called despite error
        mock_redis.delete.assert_called_once_with("key:1", "key:2")

    @pytest.mark.asyncio
    async def test_cache_delete_pattern_large_keyset(self):
        """Should handle deleting large number of keys matching pattern."""
        mock_redis = AsyncMock()

        # Simulate 100 matching keys
        async def mock_scan_iter(match):
            for i in range(100):
                yield f"batch:key:{i}"

        mock_redis.scan_iter = mock_scan_iter

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            await cache_delete_pattern("batch:key:*")

        # All 100 keys should be deleted in one call
        mock_redis.delete.assert_called_once()
        call_args = mock_redis.delete.call_args[0]
        assert len(call_args) == 100
        assert "batch:key:0" in call_args
        assert "batch:key:99" in call_args


class TestCacheHelpersIntegration:
    """Integration tests verifying cache helpers work together correctly."""

    @pytest.mark.asyncio
    async def test_set_then_get_roundtrip(self):
        """Should successfully set and retrieve the same model."""
        test_id = str(uuid4())
        model = SimpleModel(id=test_id, name="Integration Test")

        mock_redis = AsyncMock()
        stored_value = None

        # Mock setex to capture stored value
        async def mock_setex(key, ttl, value):
            nonlocal stored_value
            stored_value = value

        mock_redis.setex = mock_setex
        mock_redis.get = AsyncMock(side_effect=lambda key: stored_value)

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Set the value
            await cache_set("test:key", model, ttl=300)

            # Get it back
            result = await cache_get("test:key", SimpleModel)

        assert result is not None
        assert result.id == test_id
        assert result.name == "Integration Test"

    @pytest.mark.asyncio
    async def test_set_delete_get_sequence(self):
        """Should return None after deleting a cached value."""
        model = SimpleModel(id=str(uuid4()), name="Test")

        mock_redis = AsyncMock()
        cache_storage = {}

        async def mock_setex(key, ttl, value):
            cache_storage[key] = value

        async def mock_get(key):
            return cache_storage.get(key)

        async def mock_delete(key):
            cache_storage.pop(key, None)

        mock_redis.setex = mock_setex
        mock_redis.get = mock_get
        mock_redis.delete = mock_delete

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Set, verify it's there
            await cache_set("test:key", model, ttl=300)
            result1 = await cache_get("test:key", SimpleModel)
            assert result1 is not None

            # Delete, verify it's gone
            await cache_delete("test:key")
            result2 = await cache_get("test:key", SimpleModel)
            assert result2 is None

    @pytest.mark.asyncio
    async def test_pattern_delete_affects_multiple_keys(self):
        """Should delete all matching keys when using pattern delete."""
        models = [
            SimpleModel(id=str(uuid4()), name=f"User {i}")
            for i in range(5)
        ]

        mock_redis = AsyncMock()
        cache_storage = {}

        async def mock_setex(key, ttl, value):
            cache_storage[key] = value

        async def mock_get(key):
            return cache_storage.get(key)

        async def mock_scan_iter(match):
            for key in cache_storage.keys():
                if key.startswith("user:"):
                    yield key

        async def mock_delete(*keys):
            for key in keys:
                cache_storage.pop(key, None)

        mock_redis.setex = mock_setex
        mock_redis.get = mock_get
        mock_redis.scan_iter = mock_scan_iter
        mock_redis.delete = mock_delete

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Cache all models
            for i, model in enumerate(models):
                await cache_set(f"user:{i}", model, ttl=300)

            # Verify all are cached
            for i in range(5):
                result = await cache_get(f"user:{i}", SimpleModel)
                assert result is not None

            # Delete all with pattern
            await cache_delete_pattern("user:*")

            # Verify all are deleted
            for i in range(5):
                result = await cache_get(f"user:{i}", SimpleModel)
                assert result is None
