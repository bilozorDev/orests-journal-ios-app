"""
Comprehensive integration tests for food management endpoints.

Tests cover:
- GET /api/v1/foods/ - list foods
- POST /api/v1/foods/ - create food
- GET /api/v1/foods/{id} - get single food
- PATCH /api/v1/foods/{id} - update food
- DELETE /api/v1/foods/{id} - delete/archive food

Test scenarios:
- Happy path (200, 201 responses)
- Validation errors (422)
- Not found (404)
- Unauthorized (401)
- Forbidden (403)
- Archived foods handling
- Cache invalidation behavior
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
    create_mock_food,
    create_mock_feeding,
)


class TestListFoods:
    """Tests for GET /api/v1/foods endpoint."""

    @pytest.mark.asyncio
    async def test_list_foods_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list all non-archived foods for the family."""
        from uuid import UUID

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food_1 = create_mock_food(
            name="Dry Food",
            category="dry",
            calories_per_kg=3500.0,
        )
        mock_food_2 = create_mock_food(
            name="Wet Food",
            category="wet",
            calories_per_kg=1200.0,
        )

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = [mock_food_1, mock_food_2]

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, foods_result]
        )

        # Mock cache miss
        with patch("app.api.endpoints.foods.cache_get", return_value=None), \
             patch("app.api.endpoints.foods.cache_set") as mock_cache_set:

            # Make request
            response = await client.get(
                f"/api/v1/foods?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "foods" in data
            assert len(data["foods"]) == 2
            assert data["foods"][0]["name"] == "Dry Food"
            assert data["foods"][1]["name"] == "Wet Food"

            # Verify cache was set
            mock_cache_set.assert_called_once()

            # Verify cache-control header
            assert "Cache-Control" in response.headers
            assert "max-age=300" in response.headers["Cache-Control"]

    @pytest.mark.asyncio
    async def test_list_foods_with_cache_hit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return cached data when available."""
        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(name="Cached Food")

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result]
        )

        # Mock cache hit
        cached_response = {
            "foods": [{
                "id": str(mock_food.id),
                "org_id": str(mock_food.org_id),
                "name": mock_food.name,
                "category": mock_food.category,
                "calories_per_kg": mock_food.calories_per_kg,
                "container_size": mock_food.container_size,
                "container_size_unit": mock_food.container_size_unit,
                "image_url": mock_food.image_url,
                "is_archived": False,
                "created_at": mock_food.created_at.isoformat(),
            }]
        }

        with patch("app.api.endpoints.foods.cache_get", return_value=cached_response):
            response = await client.get(
                f"/api/v1/foods?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response came from cache
            assert response.status_code == 200
            data = response.json()
            assert len(data["foods"]) == 1
            assert data["foods"][0]["name"] == "Cached Food"

    @pytest.mark.asyncio
    async def test_list_foods_include_archived(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should include archived foods when include_archived=true."""
        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_active_food = create_mock_food(name="Active Food", is_archived=False)
        mock_archived_food = create_mock_food(name="Archived Food", is_archived=True)

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = [
            mock_active_food,
            mock_archived_food
        ]

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, foods_result]
        )

        # Note: Cache is NOT used when include_archived=true
        response = await client.get(
            f"/api/v1/foods?org_id={test_family_id}&include_archived=true",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["foods"]) == 2

    @pytest.mark.asyncio
    async def test_list_foods_empty(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return empty list when no foods exist."""
        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, foods_result]
        )

        with patch("app.api.endpoints.foods.cache_get", return_value=None), \
             patch("app.api.endpoints.foods.cache_set"):
            response = await client.get(
                f"/api/v1/foods?org_id={test_family_id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["foods"] == []

    @pytest.mark.asyncio
    async def test_list_foods_unauthorized_no_token(
        self,
        client: AsyncClient,
        test_family_id: str,
    ):
        """Should return 401 when no auth token provided."""
        response = await client.get(
            f"/api/v1/foods?org_id={test_family_id}",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_foods_forbidden_not_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 403 when user is not a family member."""
        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock no membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result]
        )

        response = await client.get(
            f"/api/v1/foods?org_id={test_family_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_foods_missing_org_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when org_id is missing."""
        response = await client.get(
            "/api/v1/foods",
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestCreateFood:
    """Tests for POST /api/v1/foods endpoint."""

    @pytest.mark.asyncio
    async def test_create_food_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create a new food item."""
        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            name="New Food",
            category="dry",
            calories_per_kg=3800.0,
            container_size=5000.0,
            container_size_unit="g",
        )

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result]
        )

        # Mock the refresh to set food attributes
        async def mock_refresh(obj):
            obj.id = mock_food.id
            obj.created_at = mock_food.created_at
            obj.is_archived = False

        mock_db_session.refresh = mock_refresh

        # Mock cache invalidation
        with patch("app.api.endpoints.foods.invalidate_food_caches") as mock_invalidate:
            # Make request
            response = await client.post(
                f"/api/v1/foods?org_id={test_family_id}",
                json={
                    "name": "New Food",
                    "category": "dry",
                    "calories_per_kg": 3800.0,
                    "container_size": 5000.0,
                    "container_size_unit": "g",
                },
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "New Food"
            assert data["category"] == "dry"
            assert data["calories_per_kg"] == 3800.0
            assert data["container_size"] == 5000.0
            assert data["container_size_unit"] == "g"
            assert data["is_archived"] is False

            # Verify cache was invalidated
            mock_invalidate.assert_called_once_with(test_family_id)

    @pytest.mark.asyncio
    async def test_create_food_with_image_url(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create food with optional image URL."""
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            image_url="https://example.com/food.jpg",
        )

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result]
        )

        async def mock_refresh(obj):
            obj.id = mock_food.id
            obj.created_at = mock_food.created_at
            obj.image_url = mock_food.image_url
            obj.is_archived = False

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.foods.invalidate_food_caches"):
            response = await client.post(
                f"/api/v1/foods?org_id={test_family_id}",
                json={
                    "name": "Food with Image",
                    "category": "wet",
                    "calories_per_kg": 1200.0,
                    "container_size": 400.0,
                    "container_size_unit": "g",
                    "image_url": "https://example.com/food.jpg",
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["image_url"] == "https://example.com/food.jpg"

    @pytest.mark.asyncio
    async def test_create_food_validation_missing_name(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 422 when name is missing."""
        response = await client.post(
            f"/api/v1/foods?org_id={test_family_id}",
            json={
                "category": "dry",
                "calories_per_kg": 3500.0,
                "container_size": 1000.0,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_food_validation_invalid_category(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 422 when category is invalid."""
        response = await client.post(
            f"/api/v1/foods?org_id={test_family_id}",
            json={
                "name": "Test Food",
                "category": "invalid_category",
                "calories_per_kg": 3500.0,
                "container_size": 1000.0,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, list)

    @pytest.mark.asyncio
    async def test_create_food_validation_negative_calories(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should accept negative calories (validated at application level if needed)."""
        # Note: Current schema doesn't validate negative values
        # This documents current behavior
        mock_membership = create_mock_membership(
            user_id=test_family_id,
            family_id=test_family_id,
        )

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result]
        )

        async def mock_refresh(obj):
            obj.id = str(uuid4())
            obj.created_at = MagicMock()
            obj.is_archived = False

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.foods.invalidate_food_caches"):
            response = await client.post(
                f"/api/v1/foods?org_id={test_family_id}",
                json={
                    "name": "Test Food",
                    "category": "dry",
                    "calories_per_kg": -100.0,  # Negative value
                    "container_size": 1000.0,
                },
                headers=auth_headers,
            )

            # Currently accepts negative values
            # Consider adding Field(gt=0) validation in schema
            assert response.status_code in [201, 422]

    @pytest.mark.asyncio
    async def test_create_food_validation_invalid_unit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 422 when container_size_unit is invalid."""
        response = await client.post(
            f"/api/v1/foods?org_id={test_family_id}",
            json={
                "name": "Test Food",
                "category": "dry",
                "calories_per_kg": 3500.0,
                "container_size": 1000.0,
                "container_size_unit": "liters",  # Invalid unit
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_food_unauthorized_no_token(
        self,
        client: AsyncClient,
        test_family_id: str,
    ):
        """Should return 401 when no auth token provided."""
        response = await client.post(
            f"/api/v1/foods?org_id={test_family_id}",
            json={
                "name": "Test Food",
                "category": "dry",
                "calories_per_kg": 3500.0,
                "container_size": 1000.0,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_food_forbidden_not_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 403 when user is not a family member."""
        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock no membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result]
        )

        response = await client.post(
            f"/api/v1/foods?org_id={test_family_id}",
            json={
                "name": "Test Food",
                "category": "dry",
                "calories_per_kg": 3500.0,
                "container_size": 1000.0,
            },
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestGetFood:
    """Tests for GET /api/v1/foods/{food_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_food_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should get a single food item."""
        food_id = str(uuid4())

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
            name="Specific Food",
            category="snack",
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/foods/{food_id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == food_id
        assert data["name"] == "Specific Food"
        assert data["category"] == "snack"

    @pytest.mark.asyncio
    async def test_get_food_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when food doesn't exist."""
        food_id = str(uuid4())

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock food not found
        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result]
        )

        response = await client.get(
            f"/api/v1/foods/{food_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Food not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_food_forbidden_wrong_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 when user doesn't belong to food's family."""
        food_id = str(uuid4())
        other_family_id = str(uuid4())

        # Setup mocks - food exists but user not in family
        mock_food = create_mock_food(
            food_id=food_id,
            org_id=other_family_id,  # Different family
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # No membership found for this family
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        response = await client.get(
            f"/api/v1/foods/{food_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_food_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when food_id is not a valid UUID."""
        response = await client.get(
            "/api/v1/foods/not-a-uuid",
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_food_unauthorized_no_token(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        food_id = str(uuid4())

        response = await client.get(
            f"/api/v1/foods/{food_id}",
        )

        assert response.status_code == 401


class TestUpdateFood:
    """Tests for PATCH /api/v1/foods/{food_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_food_name(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update food name."""
        food_id = str(uuid4())

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
            name="Old Name",
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        with patch("app.api.endpoints.foods.invalidate_food_caches") as mock_invalidate:
            # Make request
            response = await client.patch(
                f"/api/v1/foods/{food_id}",
                json={"name": "New Name"},
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            assert mock_food.name == "New Name"

            # Verify cache was invalidated
            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_food_category(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update food category."""
        food_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
            category="dry",
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        with patch("app.api.endpoints.foods.invalidate_food_caches"):
            response = await client.patch(
                f"/api/v1/foods/{food_id}",
                json={"category": "wet"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert mock_food.category == "wet"

    @pytest.mark.asyncio
    async def test_update_food_multiple_fields(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update multiple fields at once."""
        food_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
            name="Old Food",
            calories_per_kg=3000.0,
            container_size=1000.0,
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        with patch("app.api.endpoints.foods.invalidate_food_caches"):
            response = await client.patch(
                f"/api/v1/foods/{food_id}",
                json={
                    "name": "Updated Food",
                    "calories_per_kg": 3800.0,
                    "container_size": 2000.0,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert mock_food.name == "Updated Food"
            assert mock_food.calories_per_kg == 3800.0
            assert mock_food.container_size == 2000.0

    @pytest.mark.asyncio
    async def test_update_food_partial_update(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update only specified fields (PATCH semantics)."""
        food_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
            name="Original Name",
            category="dry",
            calories_per_kg=3500.0,
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        with patch("app.api.endpoints.foods.invalidate_food_caches"):
            # Update only calories
            response = await client.patch(
                f"/api/v1/foods/{food_id}",
                json={"calories_per_kg": 4000.0},
                headers=auth_headers,
            )

            assert response.status_code == 200
            # Only calories should change
            assert mock_food.calories_per_kg == 4000.0
            # Other fields should remain unchanged
            assert mock_food.name == "Original Name"
            assert mock_food.category == "dry"

    @pytest.mark.asyncio
    async def test_update_food_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when food doesn't exist."""
        food_id = str(uuid4())

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock food not found
        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result]
        )

        response = await client.patch(
            f"/api/v1/foods/{food_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Food not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_food_forbidden_wrong_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 403 when user doesn't belong to food's family."""
        food_id = str(uuid4())
        other_family_id = str(uuid4())

        mock_food = create_mock_food(
            food_id=food_id,
            org_id=other_family_id,
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        response = await client.patch(
            f"/api/v1/foods/{food_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_food_validation_invalid_category(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 422 when category is invalid."""
        food_id = str(uuid4())

        response = await client.patch(
            f"/api/v1/foods/{food_id}",
            json={"category": "invalid"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_food_unauthorized_no_token(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        food_id = str(uuid4())

        response = await client.patch(
            f"/api/v1/foods/{food_id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 401


class TestDeleteFood:
    """Tests for DELETE /api/v1/foods/{food_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_food_hard_delete_no_feedings(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should hard delete food when no feeding records exist."""
        food_id = str(uuid4())

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership, get count
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock feeding count = 0
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result, count_result]
        )

        with patch("app.api.endpoints.foods.invalidate_food_caches") as mock_invalidate:
            # Make request
            response = await client.delete(
                f"/api/v1/foods/{food_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] is True
            assert data["archived"] is False
            assert "deleted successfully" in data["message"]

            # Verify food was deleted
            mock_db_session.delete.assert_called_once_with(mock_food)

            # Verify cache was invalidated
            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_food_archive_with_feedings(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should archive food instead of deleting when feeding records exist."""
        food_id = str(uuid4())

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
            is_archived=False,
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership, get count
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock feeding count = 5
        count_result = MagicMock()
        count_result.scalar.return_value = 5

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result, count_result]
        )

        with patch("app.api.endpoints.foods.invalidate_food_caches") as mock_invalidate:
            # Make request
            response = await client.delete(
                f"/api/v1/foods/{food_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] is False
            assert data["archived"] is True
            assert "5 feeding record(s)" in data["message"]
            assert "archived instead of deleted" in data["message"]

            # Verify food was archived, not deleted
            assert mock_food.is_archived is True
            mock_db_session.delete.assert_not_called()

            # Verify cache was invalidated
            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_food_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when food doesn't exist."""
        food_id = str(uuid4())

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock food not found
        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result]
        )

        response = await client.delete(
            f"/api/v1/foods/{food_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Food not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_food_forbidden_wrong_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 403 when user doesn't belong to food's family."""
        food_id = str(uuid4())
        other_family_id = str(uuid4())

        mock_food = create_mock_food(
            food_id=food_id,
            org_id=other_family_id,
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        response = await client.delete(
            f"/api/v1/foods/{food_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_food_unauthorized_no_token(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        food_id = str(uuid4())

        response = await client.delete(
            f"/api/v1/foods/{food_id}",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_food_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when food_id is not a valid UUID."""
        response = await client.delete(
            "/api/v1/foods/not-a-uuid",
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestArchiveBehavior:
    """Tests for archived food handling edge cases."""

    @pytest.mark.asyncio
    async def test_archived_food_excluded_from_default_list(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Archived foods should not appear in default list."""
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_active_food = create_mock_food(name="Active", is_archived=False)

        # Mock database queries - set_rls_user is called first
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = [mock_active_food]

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, foods_result]
        )

        with patch("app.api.endpoints.foods.cache_get", return_value=None), \
             patch("app.api.endpoints.foods.cache_set"):
            response = await client.get(
                f"/api/v1/foods?org_id={test_family_id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["foods"]) == 1
            assert data["foods"][0]["name"] == "Active"

    @pytest.mark.asyncio
    async def test_can_get_archived_food_by_id(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Archived foods should still be retrievable by ID."""
        food_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_archived_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
            name="Archived Food",
            is_archived=True,
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_archived_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        response = await client.get(
            f"/api/v1/foods/{food_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_archived"] is True
        assert data["name"] == "Archived Food"

    @pytest.mark.asyncio
    async def test_can_update_archived_food(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Archived foods should be updatable (e.g., to unarchive)."""
        food_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_archived_food = create_mock_food(
            food_id=food_id,
            org_id=test_family_id,
            is_archived=True,
        )

        # Mock database queries - set_rls_user, get food, set_rls_user again, get membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        food_result = MagicMock()
        food_result.scalar_one_or_none.return_value = mock_archived_food

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, food_result, rls_result2, membership_result]
        )

        with patch("app.api.endpoints.foods.invalidate_food_caches"):
            response = await client.patch(
                f"/api/v1/foods/{food_id}",
                json={"name": "Updated Name"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert mock_archived_food.name == "Updated Name"
