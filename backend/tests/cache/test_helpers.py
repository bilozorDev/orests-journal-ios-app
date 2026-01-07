"""
Unit tests for cache helper functions.

Tests cache_get, cache_set, cache_delete, cache_delete_pattern, and cache_get_or_compute
functions with various scenarios including Redis availability, data serialization,
error handling, and cache stampede prevention.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel

from app.cache.helpers import (
    cache_delete,
    cache_delete_pattern,
    cache_get,
    cache_get_or_compute,
    cache_set,
    LOCK_TIMEOUT_SECONDS,
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


class TestCacheGetOrCompute:
    """Tests for cache_get_or_compute with cache stampede prevention."""

    @pytest.mark.asyncio
    async def test_returns_cached_value_without_computing(self):
        """Should return cached value without calling compute function."""
        test_id = str(uuid4())
        cached_json = f'{{"id": "{test_id}", "name": "Cached"}}'

        mock_redis = AsyncMock()
        mock_redis.get.return_value = cached_json

        compute_called = False

        async def compute_func():
            nonlocal compute_called
            compute_called = True
            return SimpleModel(id="computed", name="Computed")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get_or_compute(
                "test:key", SimpleModel, 300, compute_func
            )

        assert result.id == test_id
        assert result.name == "Cached"
        assert not compute_called

    @pytest.mark.asyncio
    async def test_computes_and_caches_when_not_cached(self):
        """Should compute and cache value when not in cache."""
        test_id = str(uuid4())

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # Not cached
        mock_redis.set.return_value = True  # Lock acquired
        mock_redis.setex = AsyncMock()  # Cache set
        mock_redis.delete = AsyncMock()  # Lock released

        async def compute_func():
            return SimpleModel(id=test_id, name="Computed")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get_or_compute(
                "test:key", SimpleModel, 300, compute_func
            )

        assert result.id == test_id
        assert result.name == "Computed"

        # Verify lock was acquired with NX flag
        mock_redis.set.assert_called_once()
        lock_call = mock_redis.set.call_args
        assert "lock:test:key" == lock_call[0][0]
        assert lock_call[1]["nx"] is True  # Atomic set-if-not-exists

        # Verify value was cached
        mock_redis.setex.assert_called_once()

        # Verify lock was released
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_computes_directly_when_cache_disabled(self):
        """Should compute directly when cache is disabled."""
        test_id = str(uuid4())
        compute_called = False

        async def compute_func():
            nonlocal compute_called
            compute_called = True
            return SimpleModel(id=test_id, name="Computed")

        with patch("app.cache.helpers.is_cache_enabled", return_value=False):
            result = await cache_get_or_compute(
                "test:key", SimpleModel, 300, compute_func
            )

        assert result.id == test_id
        assert compute_called

    @pytest.mark.asyncio
    async def test_waits_for_other_caller_when_lock_held(self):
        """Should wait and get cached value when another caller holds the lock."""
        test_id = str(uuid4())
        mock_redis = AsyncMock()

        # First call returns None (not cached)
        # Subsequent calls return cached value (after "waiting")
        get_call_count = 0

        async def mock_get(key):
            nonlocal get_call_count
            get_call_count += 1
            if get_call_count <= 1:
                return None  # First call - not cached
            return f'{{"id": "{test_id}", "name": "Cached By Other"}}'

        mock_redis.get = mock_get
        mock_redis.set = AsyncMock(return_value=False)  # Lock NOT acquired (held by other)
        mock_redis.exists = AsyncMock(return_value=True)  # Lock still held

        compute_called = False

        async def compute_func():
            nonlocal compute_called
            compute_called = True
            return SimpleModel(id="should-not-be-called", name="Computed")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis), \
             patch("app.cache.helpers.asyncio.sleep", new_callable=AsyncMock):
            result = await cache_get_or_compute(
                "test:key", SimpleModel, 300, compute_func
            )

        # Should get the value cached by the other caller
        assert result.id == test_id
        assert result.name == "Cached By Other"
        assert not compute_called

    @pytest.mark.asyncio
    async def test_computes_after_lock_timeout(self):
        """Should compute directly after waiting for lock times out."""
        test_id = str(uuid4())
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Never cached
        mock_redis.set = AsyncMock(return_value=False)  # Never acquire lock
        mock_redis.exists = AsyncMock(return_value=True)  # Lock always held

        async def compute_func():
            return SimpleModel(id=test_id, name="Timeout Fallback")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis), \
             patch("app.cache.helpers.asyncio.sleep", new_callable=AsyncMock):
            result = await cache_get_or_compute(
                "test:key", SimpleModel, 300, compute_func
            )

        # After timeout, should compute directly
        assert result.id == test_id
        assert result.name == "Timeout Fallback"

    @pytest.mark.asyncio
    async def test_acquires_lock_when_previous_holder_releases(self):
        """Should acquire lock after previous holder releases it without caching."""
        test_id = str(uuid4())
        mock_redis = AsyncMock()

        # First get returns None, subsequent returns None too (other caller failed to cache)
        mock_redis.get = AsyncMock(return_value=None)

        # First set returns False (lock held), second returns True (lock released)
        set_calls = 0

        async def mock_set(*args, **kwargs):
            nonlocal set_calls
            set_calls += 1
            return set_calls > 1  # First call fails, subsequent succeed

        mock_redis.set = mock_set

        # Lock no longer exists (previous holder released it)
        exists_calls = 0

        async def mock_exists(key):
            nonlocal exists_calls
            exists_calls += 1
            return exists_calls < 2  # First check shows lock held, then released

        mock_redis.exists = mock_exists
        mock_redis.setex = AsyncMock()
        mock_redis.delete = AsyncMock()

        async def compute_func():
            return SimpleModel(id=test_id, name="Computed After Lock Release")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis), \
             patch("app.cache.helpers.asyncio.sleep", new_callable=AsyncMock):
            result = await cache_get_or_compute(
                "test:key", SimpleModel, 300, compute_func
            )

        assert result.id == test_id
        assert result.name == "Computed After Lock Release"
        # Should have cached the value
        mock_redis.setex.assert_called()

    @pytest.mark.asyncio
    async def test_releases_lock_on_compute_error(self):
        """Should release lock even when compute function raises error."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Not cached
        mock_redis.set = AsyncMock(return_value=True)  # Lock acquired
        mock_redis.delete = AsyncMock()  # Track lock release

        async def failing_compute():
            raise ValueError("Compute failed")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            with pytest.raises(ValueError, match="Compute failed"):
                await cache_get_or_compute(
                    "test:key", SimpleModel, 300, failing_compute
                )

        # Lock should still be released
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_fallback_when_lock_acquisition_fails(self):
        """Should compute without lock when Redis lock operation fails."""
        test_id = str(uuid4())
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Not cached
        mock_redis.set = AsyncMock(side_effect=Exception("Redis error"))  # Lock acquisition fails

        async def compute_func():
            return SimpleModel(id=test_id, name="Fallback Compute")

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            result = await cache_get_or_compute(
                "test:key", SimpleModel, 300, compute_func
            )

        # Should still return computed value
        assert result.id == test_id
        assert result.name == "Fallback Compute"

    @pytest.mark.asyncio
    async def test_prevents_cache_stampede_concurrent_calls(self):
        """Should prevent cache stampede by only computing once for concurrent calls."""
        test_id = str(uuid4())
        mock_redis = AsyncMock()

        compute_count = 0
        compute_started = asyncio.Event()
        compute_can_finish = asyncio.Event()

        async def slow_compute():
            nonlocal compute_count
            compute_count += 1
            compute_started.set()
            await compute_can_finish.wait()
            return SimpleModel(id=test_id, name="Computed")

        # First caller acquires lock, others don't
        lock_acquired = False

        async def mock_set(key, value, **kwargs):
            nonlocal lock_acquired
            if "lock:" in key and not lock_acquired:
                lock_acquired = True
                return True
            return False

        # Cache storage simulation
        cached_value = None

        async def mock_get(key):
            if "lock:" not in key and cached_value:
                return cached_value
            return None

        async def mock_setex(key, ttl, value):
            nonlocal cached_value
            cached_value = value

        mock_redis.get = mock_get
        mock_redis.set = mock_set
        mock_redis.setex = mock_setex
        mock_redis.delete = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=True)

        with patch("app.cache.helpers.is_cache_enabled", return_value=True), \
             patch("app.cache.helpers.get_redis", return_value=mock_redis):
            # Start first caller (will acquire lock)
            task1 = asyncio.create_task(
                cache_get_or_compute("test:key", SimpleModel, 300, slow_compute)
            )

            # Wait for first compute to start
            await asyncio.wait_for(compute_started.wait(), timeout=1.0)

            # Start second caller with mocked sleep
            with patch("app.cache.helpers.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                sleep_count = 0

                async def controlled_sleep(delay):
                    nonlocal sleep_count
                    sleep_count += 1
                    if sleep_count > 2:
                        # After a few sleeps, let compute finish
                        compute_can_finish.set()
                        await asyncio.sleep(0.001)  # Real tiny sleep

                mock_sleep.side_effect = controlled_sleep

                task2 = asyncio.create_task(
                    cache_get_or_compute("test:key", SimpleModel, 300, slow_compute)
                )

                # Let task2 start waiting
                await asyncio.sleep(0.01)

            # If compute hasn't finished, let it finish now
            compute_can_finish.set()

            result1 = await task1
            result2 = await task2

            # Both should have the same result
            assert result1.id == test_id
            assert result2.id == test_id

            # Only ONE compute should have run (stampede prevention)
            assert compute_count == 1
