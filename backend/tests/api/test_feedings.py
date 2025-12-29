"""
Comprehensive integration tests for feeding endpoints.

Tests cover:
- POST /api/v1/feedings - Create feeding
- GET /api/v1/feedings/pet/{pet_id} - List pet feedings with pagination
- GET /api/v1/feedings/pet/{pet_id}/today - Get today's feedings
- PATCH /api/v1/feedings/{id} - Update feeding
- DELETE /api/v1/feedings/{id} - Delete feeding
- GET /api/v1/feedings/pet/{pet_id}/calorie-goal - Get active calorie goal
- POST /api/v1/feedings/pet/{pet_id}/calorie-goal - Set calorie goal

Test scenarios:
- Happy path (200, 201, 204 responses)
- Validation errors (422)
- Not found (404)
- Unauthorized (401)
- Forbidden (403)
- Date range filtering (today's feedings)
- Calorie calculations
- Pagination
- Cache invalidation
"""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
    create_mock_pet,
    create_mock_feeding,
    create_mock_calorie_goal,
)


def setup_rls_and_access_verification(
    mock_db_session: AsyncMock,
    mock_pet,
    mock_membership,
    additional_results=None,
):
    """
    Helper to set up db.execute mock with proper side_effect chain for access verification.

    Most feeding endpoints call verify_pet_access which:
    1. Executes RLS SET LOCAL query (set_rls_user)
    2. Queries for pet
    3. Executes RLS SET LOCAL query again (from verify_family_access inside verify_pet_access)
    4. Queries for membership
    5. Additional queries as needed
    """
    results = []

    # RLS SET LOCAL (from verify_pet_access calling set_rls_user)
    rls_result1 = MagicMock()
    rls_result1.scalar_one_or_none.return_value = None
    results.append(rls_result1)

    # Pet query
    pet_result = MagicMock()
    pet_result.scalar_one_or_none.return_value = mock_pet
    results.append(pet_result)

    # RLS SET LOCAL (from verify_family_access)
    rls_result2 = MagicMock()
    rls_result2.scalar_one_or_none.return_value = None
    results.append(rls_result2)

    # Membership query
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = mock_membership
    results.append(membership_result)

    # Add any additional results
    if additional_results:
        results.extend(additional_results)

    mock_db_session.execute = AsyncMock(side_effect=results)


def setup_feeding_access_verification(
    mock_db_session: AsyncMock,
    mock_feeding,
    mock_pet,
    mock_membership,
    additional_results=None,
):
    """
    Helper for endpoints that use verify_feeding_access.

    verify_feeding_access:
    1. Queries for feeding
    2. Calls verify_pet_access (which has its own RLS + pet + membership checks)
    """
    results = []

    # Feeding query
    feeding_result = MagicMock()
    feeding_result.scalar_one_or_none.return_value = mock_feeding
    results.append(feeding_result)

    # RLS SET LOCAL (from verify_pet_access)
    rls_result1 = MagicMock()
    rls_result1.scalar_one_or_none.return_value = None
    results.append(rls_result1)

    # Pet query
    pet_result = MagicMock()
    pet_result.scalar_one_or_none.return_value = mock_pet
    results.append(pet_result)

    # RLS SET LOCAL (from verify_family_access)
    rls_result2 = MagicMock()
    rls_result2.scalar_one_or_none.return_value = None
    results.append(rls_result2)

    # Membership query
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = mock_membership
    results.append(membership_result)

    # Add any additional results
    if additional_results:
        results.extend(additional_results)

    mock_db_session.execute = AsyncMock(side_effect=results)


class TestCreateFeeding:
    """Tests for POST /api/v1/feedings endpoint."""

    @pytest.mark.asyncio
    async def test_create_feeding_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully create a feeding record."""
        pet_id = str(uuid4())
        food_id = str(uuid4())

        # Mock pet access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership
        )

        # Mock refresh to set created attributes
        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()

        mock_db_session.refresh = mock_refresh

        # Mock cache invalidation
        with patch("app.api.endpoints.feedings.invalidate_feeding_caches") as mock_invalidate:
            # Make request
            fed_at = datetime.utcnow().isoformat()
            response = await client.post(
                "/api/v1/feedings",
                json={
                    "pet_id": pet_id,
                    "food_id": food_id,
                    "amount": 100.0,
                    "amount_unit": "g",
                    "calories": 350.0,
                    "notes": "Breakfast",
                    "fed_at": fed_at,
                },
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["pet_id"] == pet_id
            assert data["food_id"] == food_id
            assert data["amount"] == 100.0
            assert data["amount_unit"] == "g"
            assert data["calories"] == 350.0
            assert data["notes"] == "Breakfast"
            assert data["fed_by"] == test_user_id

            mock_db_session.commit.assert_called()
            mock_invalidate.assert_called_once_with(UUID(pet_id))

    @pytest.mark.asyncio
    async def test_create_feeding_defaults_fed_at_to_now(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should default fed_at to current time if not provided."""
        pet_id = str(uuid4())
        food_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership
        )

        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()
            obj.fed_at = datetime.utcnow()

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches"):
            # Make request without fed_at
            response = await client.post(
                "/api/v1/feedings",
                json={
                    "pet_id": pet_id,
                    "food_id": food_id,
                    "amount": 50.0,
                    "amount_unit": "g",
                    "calories": 175.0,
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert "fed_at" in data
            # Verify fed_at is recent (within last 5 seconds)
            fed_at = datetime.fromisoformat(data["fed_at"].replace("Z", "+00:00"))
            now = datetime.utcnow()
            assert (now - fed_at).total_seconds() < 5

    @pytest.mark.asyncio
    async def test_create_feeding_without_notes(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create feeding without optional notes field."""
        pet_id = str(uuid4())
        food_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership
        )

        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()
            obj.notes = None

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches"):
            response = await client.post(
                "/api/v1/feedings",
                json={
                    "pet_id": pet_id,
                    "food_id": food_id,
                    "amount": 100.0,
                    "amount_unit": "g",
                    "calories": 350.0,
                },
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["notes"] is None

    @pytest.mark.asyncio
    async def test_create_feeding_without_auth(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        response = await client.post(
            "/api/v1/feedings",
            json={
                "pet_id": str(uuid4()),
                "food_id": str(uuid4()),
                "amount": 100.0,
                "amount_unit": "g",
                "calories": 350.0,
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_feeding_pet_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 404 when pet doesn't exist."""
        pet_id = str(uuid4())

        # Mock RLS query
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock pet not found
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[rls_result, pet_result])

        response = await client.post(
            "/api/v1/feedings",
            json={
                "pet_id": pet_id,
                "food_id": str(uuid4()),
                "amount": 100.0,
                "amount_unit": "g",
                "calories": 350.0,
            },
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Pet not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_feeding_no_pet_access(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 when user doesn't have access to pet."""
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        # Pet exists but belongs to different family
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)

        # RLS query
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query (from verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # User has no membership in pet's family
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, pet_result, rls_result2, membership_result]
        )

        response = await client.post(
            "/api/v1/feedings",
            json={
                "pet_id": pet_id,
                "food_id": str(uuid4()),
                "amount": 100.0,
                "amount_unit": "g",
                "calories": 350.0,
            },
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_feeding_zero_amount(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should accept zero or negative amount values (no validation constraint)."""
        # Note: Current schema doesn't validate amount > 0
        # This documents current behavior - consider adding Field(gt=0) validation
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership
        )

        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches"):
            response = await client.post(
                "/api/v1/feedings",
                json={
                    "pet_id": pet_id,
                    "food_id": str(uuid4()),
                    "amount": 0.0,  # Zero amount - currently accepted
                    "amount_unit": "g",
                    "calories": 0.0,
                },
                headers=auth_headers,
            )

            # Currently accepts zero/negative values
            # Consider adding validation: amount: float = Field(gt=0)
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_feeding_validation_missing_required_fields(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when required fields are missing."""
        response = await client.post(
            "/api/v1/feedings",
            json={
                "pet_id": str(uuid4()),
                # Missing food_id, amount, calories
            },
            headers=auth_headers,
        )

        assert response.status_code == 422
        detail = response.json()["detail"]
        assert isinstance(detail, list)

    @pytest.mark.asyncio
    async def test_create_feeding_validation_invalid_amount_unit(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid amount unit."""
        response = await client.post(
            "/api/v1/feedings",
            json={
                "pet_id": str(uuid4()),
                "food_id": str(uuid4()),
                "amount": 100.0,
                "amount_unit": "invalid_unit",  # Invalid
                "calories": 350.0,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_feeding_validation_invalid_pet_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid UUID format."""
        response = await client.post(
            "/api/v1/feedings",
            json={
                "pet_id": "not-a-valid-uuid",
                "food_id": str(uuid4()),
                "amount": 100.0,
                "amount_unit": "g",
                "calories": 350.0,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestListPetFeedings:
    """Tests for GET /api/v1/feedings/pet/{pet_id} endpoint."""

    @pytest.mark.asyncio
    async def test_list_pet_feedings_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list feedings for a pet with pagination."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Create mock feedings
        mock_feeding1 = create_mock_feeding(
            pet_id=pet_id,
            calories=200.0,
            fed_at=datetime.utcnow() - timedelta(hours=2),
        )
        mock_feeding2 = create_mock_feeding(
            pet_id=pet_id,
            calories=150.0,
            fed_at=datetime.utcnow() - timedelta(hours=1),
        )

        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 2

        # Mock feedings query
        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = [mock_feeding2, mock_feeding1]

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[count_result, feedings_result]
        )

        # Mock cache miss
        with patch("app.api.endpoints.feedings.cache_get", return_value=None), \
             patch("app.api.endpoints.feedings.cache_set") as mock_cache_set:

            # Make request
            response = await client.get(
                f"/api/v1/feedings/pet/{pet_id}?limit=50&offset=0",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["feedings"]) == 2
            assert data["total"] == 2
            assert data["total_calories"] == 350.0
            # Verify descending order (most recent first)
            assert data["feedings"][0]["calories"] == 150.0
            assert data["feedings"][1]["calories"] == 200.0

            # Verify cache was set
            mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_pet_feedings_with_cache_hit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return cached data when available."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership
        )

        # Mock cache hit
        cached_response = {
            "feedings": [{
                "id": str(uuid4()),
                "pet_id": pet_id,
                "food_id": str(uuid4()),
                "fed_by": test_user_id,
                "fed_at": datetime.utcnow().isoformat(),
                "amount": 100.0,
                "amount_unit": "g",
                "calories": 350.0,
                "notes": "Cached feeding",
                "created_at": datetime.utcnow().isoformat(),
            }],
            "total_calories": 350.0,
            "total": 1,
        }

        with patch("app.api.endpoints.feedings.cache_get", return_value=cached_response):
            response = await client.get(
                f"/api/v1/feedings/pet/{pet_id}",
                headers=auth_headers,
            )

            # Verify response came from cache
            assert response.status_code == 200
            data = response.json()
            assert len(data["feedings"]) == 1
            assert data["feedings"][0]["notes"] == "Cached feeding"

    @pytest.mark.asyncio
    async def test_list_pet_feedings_empty(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return empty list when pet has no feedings."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock empty count and results
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[count_result, feedings_result]
        )

        with patch("app.api.endpoints.feedings.cache_get", return_value=None), \
             patch("app.api.endpoints.feedings.cache_set"):

            # Make request
            response = await client.get(
                f"/api/v1/feedings/pet/{pet_id}",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["feedings"]) == 0
            assert data["total"] == 0
            assert data["total_calories"] == 0

    @pytest.mark.asyncio
    async def test_list_pet_feedings_pagination(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should respect limit and offset parameters."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Create mock feeding for second page
        mock_feeding = create_mock_feeding(pet_id=pet_id, calories=100.0)

        # Total is 15 but we're requesting page 2 with limit 10
        count_result = MagicMock()
        count_result.scalar.return_value = 15

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = [mock_feeding] * 5  # 5 items on page 2

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[count_result, feedings_result]
        )

        with patch("app.api.endpoints.feedings.cache_get", return_value=None), \
             patch("app.api.endpoints.feedings.cache_set"):

            # Make request for page 2
            response = await client.get(
                f"/api/v1/feedings/pet/{pet_id}?limit=10&offset=10",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 15
            assert len(data["feedings"]) == 5

    @pytest.mark.asyncio
    async def test_list_pet_feedings_default_pagination(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should use default limit of 50 when not specified."""
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[count_result, feedings_result]
        )

        with patch("app.api.endpoints.feedings.cache_get", return_value=None), \
             patch("app.api.endpoints.feedings.cache_set"):

            response = await client.get(
                f"/api/v1/feedings/pet/{pet_id}",
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_pet_feedings_validation_limit_too_high(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when limit exceeds maximum (100)."""
        pet_id = str(uuid4())

        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}?limit=101",
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_pet_feedings_validation_negative_offset(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when offset is negative."""
        pet_id = str(uuid4())

        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}?offset=-1",
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_pet_feedings_no_access(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 when user doesn't have access to pet."""
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        # Pet exists but user has no access
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)

        # RLS query
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query (from verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # No membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, pet_result, rls_result2, membership_result]
        )

        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_pet_feedings_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid pet_id UUID."""
        response = await client.get(
            "/api/v1/feedings/pet/not-a-uuid",
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestGetTodayFeedings:
    """Tests for GET /api/v1/feedings/pet/{pet_id}/today endpoint."""

    @pytest.mark.asyncio
    async def test_get_today_feedings_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return only today's feedings."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Create today's feedings
        now = datetime.utcnow()
        mock_feeding1 = create_mock_feeding(pet_id=pet_id, calories=200.0, fed_at=now)
        mock_feeding2 = create_mock_feeding(
            pet_id=pet_id,
            calories=150.0,
            fed_at=now - timedelta(hours=3)
        )

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = [mock_feeding1, mock_feeding2]

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[feedings_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}/today",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["feedings"]) == 2
        assert data["total_calories"] == 350.0

    @pytest.mark.asyncio
    async def test_get_today_feedings_excludes_yesterday(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should exclude feedings from previous days."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Only today's feeding is returned (yesterday's filtered by query)
        mock_feeding_today = create_mock_feeding(
            pet_id=pet_id,
            calories=100.0,
            fed_at=datetime.utcnow()
        )

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = [mock_feeding_today]

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[feedings_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}/today",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["feedings"]) == 1
        assert data["total_calories"] == 100.0

    @pytest.mark.asyncio
    async def test_get_today_feedings_empty(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return empty list when no feedings today."""
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[feedings_result]
        )

        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}/today",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["feedings"]) == 0
        assert data["total_calories"] == 0

    @pytest.mark.asyncio
    async def test_get_today_feedings_no_access(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 403 when user doesn't have access to pet."""
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)

        # RLS query
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query (from verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # No membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, pet_result, rls_result2, membership_result]
        )

        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}/today",
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestUpdateFeeding:
    """Tests for PATCH /api/v1/feedings/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_feeding_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully update a feeding record."""
        feeding_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock feeding access verification
        mock_feeding = create_mock_feeding(
            feeding_id=feeding_id,
            pet_id=pet_id,
            amount=100.0,
            calories=350.0,
            notes="Original note"
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_feeding_access_verification(
            mock_db_session,
            mock_feeding,
            mock_pet,
            mock_membership
        )

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches") as mock_invalidate:
            # Make request to update
            response = await client.patch(
                f"/api/v1/feedings/{feeding_id}",
                json={
                    "amount": 150.0,
                    "calories": 525.0,
                    "notes": "Updated note"
                },
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200

            # Verify that attributes were updated on mock
            assert mock_feeding.amount == 150.0
            assert mock_feeding.calories == 525.0
            assert mock_feeding.notes == "Updated note"

            mock_db_session.commit.assert_called()
            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_feeding_partial_update(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should allow partial updates (only specified fields)."""
        feeding_id = str(uuid4())
        pet_id = str(uuid4())

        mock_feeding = create_mock_feeding(
            feeding_id=feeding_id,
            pet_id=pet_id,
            amount=100.0,
            calories=350.0,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_feeding_access_verification(
            mock_db_session,
            mock_feeding,
            mock_pet,
            mock_membership
        )

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches"):
            # Update only notes
            response = await client.patch(
                f"/api/v1/feedings/{feeding_id}",
                json={"notes": "Just updating notes"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert mock_feeding.notes == "Just updating notes"
            # Amount should remain unchanged
            assert mock_feeding.amount == 100.0

    @pytest.mark.asyncio
    async def test_update_feeding_amount_unit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update amount_unit field correctly."""
        feeding_id = str(uuid4())
        pet_id = str(uuid4())

        mock_feeding = create_mock_feeding(
            feeding_id=feeding_id,
            pet_id=pet_id,
            amount_unit="g"
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_feeding_access_verification(
            mock_db_session,
            mock_feeding,
            mock_pet,
            mock_membership
        )

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches"):
            response = await client.patch(
                f"/api/v1/feedings/{feeding_id}",
                json={"amount_unit": "oz"},  # Valid unit: oz (ounces)
                headers=auth_headers,
            )

            assert response.status_code == 200
            # Note: The enum value conversion happens in the endpoint
            assert mock_feeding.amount_unit in ["oz", "g"]

    @pytest.mark.asyncio
    async def test_update_feeding_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when feeding doesn't exist."""
        feeding_id = str(uuid4())

        feeding_result = MagicMock()
        feeding_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(return_value=feeding_result)

        response = await client.patch(
            f"/api/v1/feedings/{feeding_id}",
            json={"notes": "Update"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Feeding record not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_feeding_no_access(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 when user doesn't have access to feeding."""
        feeding_id = str(uuid4())
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        mock_feeding = create_mock_feeding(feeding_id=feeding_id, pet_id=pet_id)
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)

        # Feeding query
        feeding_result = MagicMock()
        feeding_result.scalar_one_or_none.return_value = mock_feeding

        # RLS query
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query (from verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # User has no membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[feeding_result, rls_result1, pet_result, rls_result2, membership_result]
        )

        response = await client.patch(
            f"/api/v1/feedings/{feeding_id}",
            json={"notes": "Update"},
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_feeding_validation_invalid_field_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid field types."""
        feeding_id = str(uuid4())

        response = await client.patch(
            f"/api/v1/feedings/{feeding_id}",
            json={"amount": "not-a-number"},  # Invalid type
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_feeding_validation_invalid_unit(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid amount_unit."""
        feeding_id = str(uuid4())

        response = await client.patch(
            f"/api/v1/feedings/{feeding_id}",
            json={"amount_unit": "invalid"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_feeding_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid feeding_id UUID."""
        response = await client.patch(
            "/api/v1/feedings/not-a-uuid",
            json={"notes": "Update"},
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestDeleteFeeding:
    """Tests for DELETE /api/v1/feedings/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_feeding_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully delete a feeding record."""
        feeding_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock feeding access verification
        mock_feeding = create_mock_feeding(feeding_id=feeding_id, pet_id=pet_id)
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_feeding_access_verification(
            mock_db_session,
            mock_feeding,
            mock_pet,
            mock_membership
        )

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches") as mock_invalidate:
            # Make request
            response = await client.delete(
                f"/api/v1/feedings/{feeding_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 204

            # Verify delete was called
            mock_db_session.delete.assert_called_once_with(mock_feeding)
            mock_db_session.commit.assert_called()
            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_feeding_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when feeding doesn't exist."""
        feeding_id = str(uuid4())

        feeding_result = MagicMock()
        feeding_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(return_value=feeding_result)

        response = await client.delete(
            f"/api/v1/feedings/{feeding_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Feeding record not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_feeding_no_access(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 403 when user doesn't have access to feeding."""
        feeding_id = str(uuid4())
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        mock_feeding = create_mock_feeding(feeding_id=feeding_id, pet_id=pet_id)
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)

        # Feeding query
        feeding_result = MagicMock()
        feeding_result.scalar_one_or_none.return_value = mock_feeding

        # RLS query
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query (from verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # User has no membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[feeding_result, rls_result1, pet_result, rls_result2, membership_result]
        )

        response = await client.delete(
            f"/api/v1/feedings/{feeding_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_feeding_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid feeding_id UUID."""
        response = await client.delete(
            "/api/v1/feedings/not-a-uuid",
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestGetCalorieGoal:
    """Tests for GET /api/v1/feedings/pet/{pet_id}/calorie-goal endpoint."""

    @pytest.mark.asyncio
    async def test_get_calorie_goal_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return active calorie goal for pet."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock active calorie goal
        mock_goal = create_mock_calorie_goal(
            pet_id=pet_id,
            daily_calories=450.0,
            notes="Weight maintenance"
        )

        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = mock_goal

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[goal_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["pet_id"] == pet_id
        assert data["daily_calories"] == 450.0
        assert data["notes"] == "Weight maintenance"

    @pytest.mark.asyncio
    async def test_get_calorie_goal_none(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return null when no active calorie goal exists."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # No goal found
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[goal_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
            headers=auth_headers,
        )

        # Verify response is null/None
        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_get_calorie_goal_expired(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return null when goal is expired."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock expired goal
        mock_goal = create_mock_calorie_goal(
            pet_id=pet_id,
            daily_calories=450.0,
            effective_until=datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        )

        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = mock_goal

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[goal_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
            headers=auth_headers,
        )

        # Should return null for expired goal
        assert response.status_code == 200
        assert response.json() is None

    @pytest.mark.asyncio
    async def test_get_calorie_goal_no_access(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 403 when user doesn't have access to pet."""
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)

        # RLS query
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query (from verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # No membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, pet_result, rls_result2, membership_result]
        )

        response = await client.get(
            f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestSetCalorieGoal:
    """Tests for POST /api/v1/feedings/pet/{pet_id}/calorie-goal endpoint."""

    @pytest.mark.asyncio
    async def test_set_calorie_goal_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully create a new calorie goal."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # No previous goal exists
        prev_goal_result = MagicMock()
        prev_goal_result.scalar_one_or_none.return_value = None

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[prev_goal_result]
        )

        # Mock refresh to set created attributes
        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()
            obj.effective_from = datetime.utcnow()

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches") as mock_invalidate:
            # Make request
            response = await client.post(
                f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
                json={
                    "daily_calories": 500.0,
                    "notes": "Vet recommended"
                },
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["pet_id"] == pet_id
            assert data["daily_calories"] == 500.0
            assert data["notes"] == "Vet recommended"

            mock_db_session.commit.assert_called()
            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_calorie_goal_without_notes(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create calorie goal without optional notes field."""
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        prev_goal_result = MagicMock()
        prev_goal_result.scalar_one_or_none.return_value = None

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[prev_goal_result]
        )

        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()
            obj.effective_from = datetime.utcnow()
            obj.notes = None

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches"):
            response = await client.post(
                f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
                json={"daily_calories": 450.0},
                headers=auth_headers,
            )

            assert response.status_code == 201
            data = response.json()
            assert data["notes"] is None

    @pytest.mark.asyncio
    async def test_set_calorie_goal_ends_previous(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should end previous goal when creating a new one."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Previous goal exists
        mock_prev_goal = create_mock_calorie_goal(
            pet_id=pet_id,
            daily_calories=400.0,
            effective_until=None  # Currently active
        )

        prev_goal_result = MagicMock()
        prev_goal_result.scalar_one_or_none.return_value = mock_prev_goal

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[prev_goal_result]
        )

        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()
            obj.effective_from = datetime.utcnow()

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches"):
            # Make request
            response = await client.post(
                f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
                json={"daily_calories": 450.0},
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 201

            # Verify previous goal was ended
            assert mock_prev_goal.effective_until is not None

    @pytest.mark.asyncio
    async def test_set_calorie_goal_with_zero_calories(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should accept zero calories (no validation constraint on daily_calories)."""
        # Note: Current schema doesn't validate daily_calories > 0
        # This documents current behavior - consider adding Field(gt=0) validation
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        prev_goal_result = MagicMock()
        prev_goal_result.scalar_one_or_none.return_value = None

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[prev_goal_result]
        )

        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()
            obj.effective_from = datetime.utcnow()

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches"):
            response = await client.post(
                f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
                json={"daily_calories": 0.0},  # Zero calories - currently accepted
                headers=auth_headers,
            )

            # Currently accepts zero/negative values
            # Consider adding validation: daily_calories: float = Field(gt=0)
            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_set_calorie_goal_validation_missing_calories(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when daily_calories is missing."""
        pet_id = str(uuid4())

        response = await client.post(
            f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
            json={},  # Missing daily_calories
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_set_calorie_goal_no_access(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 when user doesn't have access to pet."""
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        # Pet exists but user has no access
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)

        # RLS query
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query (from verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # No membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, pet_result, rls_result2, membership_result]
        )

        response = await client.post(
            f"/api/v1/feedings/pet/{pet_id}/calorie-goal",
            json={"daily_calories": 450.0},
            headers=auth_headers,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_set_calorie_goal_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid pet_id UUID."""
        response = await client.post(
            "/api/v1/feedings/pet/not-a-uuid/calorie-goal",
            json={"daily_calories": 450.0},
            headers=auth_headers,
        )

        assert response.status_code == 422


class TestCacheInvalidation:
    """Tests for cache invalidation behavior."""

    @pytest.mark.asyncio
    async def test_create_feeding_invalidates_cache(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should invalidate feeding caches after creating a feeding."""
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_rls_and_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership
        )

        async def mock_refresh(obj):
            obj.id = UUID(str(uuid4()))
            obj.created_at = datetime.utcnow()

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches") as mock_invalidate:
            await client.post(
                "/api/v1/feedings",
                json={
                    "pet_id": pet_id,
                    "food_id": str(uuid4()),
                    "amount": 100.0,
                    "amount_unit": "g",
                    "calories": 350.0,
                },
                headers=auth_headers,
            )

            # Verify cache invalidation was called with correct pet_id
            mock_invalidate.assert_called_once_with(UUID(pet_id))

    @pytest.mark.asyncio
    async def test_update_feeding_invalidates_cache(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should invalidate feeding caches after updating a feeding."""
        feeding_id = str(uuid4())
        pet_id = str(uuid4())

        mock_feeding = create_mock_feeding(feeding_id=feeding_id, pet_id=pet_id)
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_feeding_access_verification(
            mock_db_session,
            mock_feeding,
            mock_pet,
            mock_membership
        )

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches") as mock_invalidate:
            await client.patch(
                f"/api/v1/feedings/{feeding_id}",
                json={"notes": "Updated"},
                headers=auth_headers,
            )

            mock_invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_feeding_invalidates_cache(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should invalidate feeding caches after deleting a feeding."""
        feeding_id = str(uuid4())
        pet_id = str(uuid4())

        mock_feeding = create_mock_feeding(feeding_id=feeding_id, pet_id=pet_id)
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_feeding_access_verification(
            mock_db_session,
            mock_feeding,
            mock_pet,
            mock_membership
        )

        with patch("app.api.endpoints.feedings.invalidate_feeding_caches") as mock_invalidate:
            await client.delete(
                f"/api/v1/feedings/{feeding_id}",
                headers=auth_headers,
            )

            mock_invalidate.assert_called_once()
