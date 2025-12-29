"""
Comprehensive integration tests for health event endpoints.

Tests cover:
- Health category management (list categories)
- Health event CRUD operations (list, create, get, update, delete)
- Health event search and filtering
- Health event photo management
- Authorization checks (owner vs member, wrong org)
- Validation errors
- Edge cases (fuzzy matching, date filtering, category cleanup)

NOTE: These tests mock the database session and use the FastAPI test client.
All authorization functions (verify_pet_access, verify_health_event_access, etc.)
call set_rls_user() first, which requires an RLS mock result in side_effect.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
    create_mock_pet,
)


# ============== Helper Functions ==============

def create_mock_category(
    category_id: str = None,
    org_id: str = TEST_FAMILY_ID,
    name: str = "Vomiting",
    name_normalized: str = None,
    created_by: str = None,
) -> MagicMock:
    """Create a mock PetHealthCategory object."""
    category = MagicMock()
    category.id = UUID(category_id) if category_id else uuid4()
    category.org_id = UUID(org_id)
    category.name = name
    category.name_normalized = name_normalized or name.lower().strip()
    category.created_by = UUID(created_by) if created_by else uuid4()
    category.created_at = datetime(2024, 1, 1)
    return category


def create_mock_event(
    event_id: str = None,
    pet_id: str = None,
    category_id: str = None,
    occurred_at: datetime = None,
    notes: str = None,
    created_by: str = None,
) -> MagicMock:
    """Create a mock PetHealthEvent object."""
    event = MagicMock()
    event.id = UUID(event_id) if event_id else uuid4()
    event.pet_id = UUID(pet_id) if pet_id else uuid4()
    event.category_id = UUID(category_id) if category_id else uuid4()
    event.occurred_at = occurred_at or datetime(2024, 1, 1)
    event.notes = notes
    event.created_by = UUID(created_by) if created_by else uuid4()
    event.created_at = datetime(2024, 1, 1)
    event.photos = []
    return event


def create_mock_photo(
    photo_id: str = None,
    event_id: str = None,
    photo_url: str = "https://example.com/photo.jpg",
    sort_order: int = 0,
) -> MagicMock:
    """Create a mock PetHealthEventPhoto object."""
    photo = MagicMock()
    photo.id = UUID(photo_id) if photo_id else uuid4()
    photo.event_id = UUID(event_id) if event_id else uuid4()
    photo.photo_url = photo_url
    photo.sort_order = sort_order
    photo.created_at = datetime(2024, 1, 1)
    return photo


# ============== List Categories Tests ==============

class TestListCategories:
    """Tests for GET /api/v1/health/pet/{pet_id}/categories endpoint."""

    @pytest.mark.asyncio
    async def test_list_categories_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list all categories for the pet's family."""
        pet_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )
        mock_cat1 = create_mock_category(
            org_id=test_family_id,
            name="Vomiting",
        )
        mock_cat2 = create_mock_category(
            org_id=test_family_id,
            name="Diarrhea",
        )

        # Mock database queries
        # 1. RLS call
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # 2. Pet lookup
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # 3. Family membership check (nested in verify_pet_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # 4. Categories query
        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_cat1, mock_cat2]

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, pet_result, rls_result2, membership_result, categories_result]
        )

        # Make request with mocked cache
        with patch("app.api.endpoints.health.cache_get", return_value=None), \
             patch("app.api.endpoints.health.cache_set"):
            response = await client.get(
                f"/api/v1/health/pet/{pet_id}/categories",
                headers=auth_headers,
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Vomiting"
        assert data[1]["name"] == "Diarrhea"

    @pytest.mark.asyncio
    async def test_list_categories_empty(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return empty list when no categories exist."""
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )

        # Mock RLS, pet access, and empty categories
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, pet_result, rls_result2, membership_result, categories_result]
        )

        with patch("app.api.endpoints.health.cache_get", return_value=None), \
             patch("app.api.endpoints.health.cache_set"):
            response = await client.get(
                f"/api/v1/health/pet/{pet_id}/categories",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_categories_unauthorized_not_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 403 if user not member of pet's family."""
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )

        # Mock RLS, pet lookup, but no membership
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None  # No membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, pet_result, rls_result2, membership_result]
        )

        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/categories",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_categories_pet_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 if pet doesn't exist."""
        pet_id = str(uuid4())

        # Mock RLS and pet not found
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = None  # Pet not found

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, pet_result]
        )

        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/categories",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Pet not found" in response.json()["detail"]


# ============== Create Health Event Tests ==============

class TestCreateHealthEvent:
    """Tests for POST /api/v1/health/pet/{pet_id}/events endpoint."""

    @pytest.mark.asyncio
    async def test_create_event_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create health event with new category."""
        pet_id = str(uuid4())
        category_id = str(uuid4())
        event_id = str(uuid4())

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )
        mock_category = create_mock_category(
            category_id=category_id,
            org_id=test_family_id,
            name="Vomiting",
        )
        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            notes="Threw up after eating",
        )

        # Mock database queries
        # 1-4: verify_pet_access (RLS, pet, RLS, membership)
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # 5. Insert category (upsert pattern, no result needed)
        # 6. Fetch category after upsert
        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        # 7. Reload event with photos
        event_result = MagicMock()
        event_result.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                MagicMock(),  # Insert category
                category_result,  # Fetch category
                event_result,  # Reload event
            ]
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.flush = AsyncMock()

        # Mock cache and notifications
        with patch("app.api.endpoints.health.invalidate_health_cache") as mock_invalidate, \
             patch("app.api.endpoints.health.notify_family_health_event") as mock_notify:
            response = await client.post(
                f"/api/v1/health/pet/{pet_id}/events",
                json={
                    "category_name": "Vomiting",
                    "notes": "Threw up after eating",
                    "notify_family": False,
                },
                headers=auth_headers,
            )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == event_id
        assert data["category_id"] == category_id
        assert data["notes"] == "Threw up after eating"
        assert data["photos"] == []

        # Verify cache invalidated
        mock_invalidate.assert_called_once_with(UUID(pet_id), UUID(test_family_id))

        # Verify notification NOT sent
        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_event_with_notify_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should send notification to family when notify_family=true."""
        pet_id = str(uuid4())
        category_id = str(uuid4())
        event_id = str(uuid4())

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
            name="Buddy",
        )
        mock_category = create_mock_category(
            category_id=category_id,
            org_id=test_family_id,
            name="Seizure",
        )
        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )

        # Mock queries
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        event_result = MagicMock()
        event_result.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                MagicMock(),  # Insert
                category_result,
                event_result,
            ]
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.flush = AsyncMock()

        # Mock cache and notifications
        with patch("app.api.endpoints.health.invalidate_health_cache"), \
             patch("app.api.endpoints.health.notify_family_health_event") as mock_notify:
            response = await client.post(
                f"/api/v1/health/pet/{pet_id}/events",
                json={
                    "category_name": "Seizure",
                    "notify_family": True,
                },
                headers=auth_headers,
            )

        assert response.status_code == 201

        # Verify notification sent with correct args
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args[0]
        assert call_args[1] == UUID(test_family_id)  # org_id
        assert call_args[2] == UUID(test_user_id)  # exclude_user_id
        assert call_args[3] == "Buddy"  # pet_name
        assert call_args[4] == "Seizure"  # category_name

    @pytest.mark.asyncio
    async def test_create_event_with_custom_occurred_at(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should allow custom occurred_at timestamp."""
        pet_id = str(uuid4())
        category_id = str(uuid4())
        event_id = str(uuid4())

        custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_category = create_mock_category(category_id=category_id, org_id=test_family_id)
        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            occurred_at=custom_time.replace(tzinfo=None),  # DB stores naive UTC
        )

        # Setup mocks
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        event_result = MagicMock()
        event_result.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                MagicMock(), category_result, event_result,
            ]
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.flush = AsyncMock()

        with patch("app.api.endpoints.health.invalidate_health_cache"):
            response = await client.post(
                f"/api/v1/health/pet/{pet_id}/events",
                json={
                    "category_name": "Vomiting",
                    "occurred_at": custom_time.isoformat(),
                },
                headers=auth_headers,
            )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_event_validation_future_date(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should reject event with future occurred_at date."""
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Mock pet access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, pet_result, rls_result2, membership_result]
        )

        # Try to create event in the future (more than 1 minute ahead)
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)

        response = await client.post(
            f"/api/v1/health/pet/{pet_id}/events",
            json={
                "category_name": "Vomiting",
                "occurred_at": future_time.isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "cannot be in the future" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_event_validation_missing_category(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 422 if category_name is missing."""
        pet_id = str(uuid4())

        response = await client.post(
            f"/api/v1/health/pet/{pet_id}/events",
            json={
                "notes": "Some notes",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_create_event_reuses_existing_category(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should reuse existing category with same normalized name."""
        pet_id = str(uuid4())
        category_id = str(uuid4())
        event_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        # Category with slightly different case
        mock_category = create_mock_category(
            category_id=category_id,
            org_id=test_family_id,
            name="Vomiting",
            name_normalized="vomiting",
        )
        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )

        # Setup mocks
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Upsert will do nothing (category exists), fetch returns existing
        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        event_result = MagicMock()
        event_result.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                MagicMock(),  # Insert (does nothing)
                category_result,  # Fetch existing
                event_result,
            ]
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.flush = AsyncMock()

        with patch("app.api.endpoints.health.invalidate_health_cache"):
            response = await client.post(
                f"/api/v1/health/pet/{pet_id}/events",
                json={
                    "category_name": "VOMITING",  # Different case
                },
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["category_id"] == category_id  # Reused existing category


# ============== List Health Events Tests ==============

class TestListHealthEvents:
    """Tests for GET /api/v1/health/pet/{pet_id}/events endpoint."""

    @pytest.mark.asyncio
    async def test_list_events_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list health events with categories."""
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_category = create_mock_category(category_id=category_id, org_id=test_family_id)
        mock_event = create_mock_event(
            pet_id=pet_id,
            category_id=category_id,
            notes="First event",
        )

        # Mock queries
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Categories query
        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        # Events query
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                categories_result,
                events_result,
            ]
        )

        with patch("app.api.endpoints.health.cache_get", return_value=None), \
             patch("app.api.endpoints.health.cache_set"):
            response = await client.get(
                f"/api/v1/health/pet/{pet_id}/events",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["event"]["notes"] == "First event"
        assert data["events"][0]["category"]["id"] == str(category_id)

    @pytest.mark.asyncio
    async def test_list_events_with_category_filter(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should filter events by category name (fuzzy match)."""
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_category = create_mock_category(
            category_id=category_id,
            org_id=test_family_id,
            name="Vomiting",
            name_normalized="vomiting",
        )
        mock_event = create_mock_event(pet_id=pet_id, category_id=category_id)

        # Mock queries
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Categories with filter (fuzzy match "vomit")
        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        # Events filtered by category
        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                categories_result,
                events_result,
            ]
        )

        # Request with category filter
        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/events?category=vomit",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1

    @pytest.mark.asyncio
    async def test_list_events_with_time_range(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should filter events by time range (since/until)."""
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_category = create_mock_category(category_id=category_id, org_id=test_family_id)
        mock_event = create_mock_event(
            pet_id=pet_id,
            category_id=category_id,
            occurred_at=datetime(2024, 2, 1, 12, 0),
        )

        # Mock queries
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                categories_result,
                events_result,
            ]
        )

        # Request with time range
        since = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()
        until = datetime(2024, 3, 1, tzinfo=timezone.utc).isoformat()

        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/events?since={since}&until={until}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1

    @pytest.mark.asyncio
    async def test_list_events_pagination(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should support pagination with limit and offset."""
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_category = create_mock_category(category_id=category_id, org_id=test_family_id)

        # Create 2 events for page 2 (offset=50, limit=50)
        mock_event1 = create_mock_event(pet_id=pet_id, category_id=category_id)
        mock_event2 = create_mock_event(pet_id=pet_id, category_id=category_id)

        # Mock queries
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event1, mock_event2]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                categories_result,
                events_result,
            ]
        )

        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/events?limit=50&offset=50",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2

    @pytest.mark.asyncio
    async def test_list_events_empty(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return empty list when no events exist."""
        pet_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Mock queries
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = []

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                categories_result,
                events_result,
            ]
        )

        with patch("app.api.endpoints.health.cache_get", return_value=None), \
             patch("app.api.endpoints.health.cache_set"):
            response = await client.get(
                f"/api/v1/health/pet/{pet_id}/events",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json() == {"events": []}


# ============== Get Single Event Tests ==============

class TestGetHealthEvent:
    """Tests for GET /api/v1/health/events/{event_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_event_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should get single health event with category."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            notes="Test notes",
        )
        mock_category = create_mock_category(
            category_id=category_id,
            org_id=test_family_id,
        )

        # Mock verify_health_event_access (checks event exists and user has access)
        # 1. Event lookup
        event_lookup_result = MagicMock()
        event_lookup_result.scalar_one_or_none.return_value = mock_event

        # 2-5. verify_pet_access (RLS, pet, RLS, membership)
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # 6. Event with category query
        event_category_result = MagicMock()
        event_category_result.one.return_value = (mock_event, mock_category)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup_result,
                rls_result, pet_result, rls_result2, membership_result,
                event_category_result,
            ]
        )

        response = await client.get(
            f"/api/v1/health/events/{event_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event"]["id"] == event_id
        assert data["event"]["notes"] == "Test notes"
        assert data["category"]["id"] == str(category_id)

    @pytest.mark.asyncio
    async def test_get_event_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 if event doesn't exist."""
        event_id = str(uuid4())

        # Mock event not found
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[event_result])

        response = await client.get(
            f"/api/v1/health/events/{event_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Health event not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_event_unauthorized(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 403 if user doesn't have access to event's pet."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Mock event found, but no family membership
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None  # No membership

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result,
                rls_result, pet_result, rls_result2, membership_result,
            ]
        )

        response = await client.get(
            f"/api/v1/health/events/{event_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]


# ============== Update Health Event Tests ==============

class TestUpdateHealthEvent:
    """Tests for PATCH /api/v1/health/events/{event_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_event_notes(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update event notes."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            notes="Old notes",
        )
        mock_category = create_mock_category(
            category_id=category_id,
            org_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Update notes
        mock_event.notes = "Updated notes"

        # Mock verify_health_event_access
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Get current category
        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        # Reload event
        reload_result = MagicMock()
        reload_result.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                category_result,
                reload_result,
            ]
        )
        mock_db_session.commit = AsyncMock()

        with patch("app.api.endpoints.health.invalidate_health_cache"):
            response = await client.patch(
                f"/api/v1/health/events/{event_id}",
                json={"notes": "Updated notes"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["event"]["notes"] == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_event_category(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update event category and cleanup orphaned category."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        old_category_id = str(uuid4())
        new_category_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=old_category_id,
        )
        mock_old_category = create_mock_category(
            category_id=old_category_id,
            org_id=test_family_id,
            name="Vomiting",
        )
        mock_new_category = create_mock_category(
            category_id=new_category_id,
            org_id=test_family_id,
            name="Diarrhea",
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Update category
        mock_event.category_id = UUID(new_category_id)

        # Mock queries
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        old_category_result = MagicMock()
        old_category_result.scalar_one.return_value = mock_old_category

        # get_or_create_category: insert new, fetch new
        new_category_result = MagicMock()
        new_category_result.scalar_one.return_value = mock_new_category

        # Reload event
        reload_result = MagicMock()
        reload_result.scalar_one.return_value = mock_event

        # Delete orphaned category
        delete_result = MagicMock()
        delete_result.rowcount = 1  # Deletion successful

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                old_category_result,
                MagicMock(),  # Insert new category
                new_category_result,  # Fetch new category
                delete_result,  # Delete old category
                reload_result,
            ]
        )
        mock_db_session.commit = AsyncMock()
        mock_db_session.flush = AsyncMock()

        with patch("app.api.endpoints.health.invalidate_health_cache"):
            response = await client.patch(
                f"/api/v1/health/events/{event_id}",
                json={"category_name": "Diarrhea"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["category"]["id"] == new_category_id

    @pytest.mark.asyncio
    async def test_update_event_occurred_at(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update event occurred_at timestamp."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        new_time = datetime(2024, 2, 15, 14, 30, 0, tzinfo=timezone.utc)

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            occurred_at=datetime(2024, 1, 1),
        )
        mock_category = create_mock_category(
            category_id=category_id,
            org_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Update occurred_at
        mock_event.occurred_at = new_time.replace(tzinfo=None)

        # Mock queries
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        reload_result = MagicMock()
        reload_result.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                category_result,
                reload_result,
            ]
        )
        mock_db_session.commit = AsyncMock()

        with patch("app.api.endpoints.health.invalidate_health_cache"):
            response = await client.patch(
                f"/api/v1/health/events/{event_id}",
                json={"occurred_at": new_time.isoformat()},
                headers=auth_headers,
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_event_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 if event doesn't exist."""
        event_id = str(uuid4())

        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[event_result])

        response = await client.patch(
            f"/api/v1/health/events/{event_id}",
            json={"notes": "New notes"},
            headers=auth_headers,
        )

        assert response.status_code == 404


# ============== Delete Health Event Tests ==============

class TestDeleteHealthEvent:
    """Tests for DELETE /api/v1/health/events/{event_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_event_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete health event and cleanup orphaned category."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Mock verify_health_event_access
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Get pet for org_id
        pet_query_result = MagicMock()
        pet_query_result.scalar_one.return_value = mock_pet

        # Get photos (none in this case)
        photos_result = MagicMock()
        photos_result.scalars.return_value.all.return_value = []

        # Delete orphaned category
        delete_category_result = MagicMock()
        delete_category_result.rowcount = 1

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                pet_query_result,
                photos_result,
                delete_category_result,
            ]
        )
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()

        with patch("app.api.endpoints.health.invalidate_health_cache"):
            response = await client.delete(
                f"/api/v1/health/events/{event_id}",
                headers=auth_headers,
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_event_with_photos(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete event and its photos from R2."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Event has 2 photos
        photo1 = create_mock_photo(
            event_id=event_id,
            photo_url="https://example.com/photo1.jpg",
        )
        photo2 = create_mock_photo(
            event_id=event_id,
            photo_url="https://example.com/photo2.jpg",
        )

        # Mock queries
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        pet_query_result = MagicMock()
        pet_query_result.scalar_one.return_value = mock_pet

        photos_result = MagicMock()
        photos_result.scalars.return_value.all.return_value = [photo1, photo2]

        delete_category_result = MagicMock()
        delete_category_result.rowcount = 0  # Category still has other events

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                pet_query_result,
                photos_result,
                delete_category_result,
            ]
        )
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Mock storage service
        mock_storage = AsyncMock()
        mock_storage.delete_image.return_value = True

        with patch("app.api.endpoints.health.invalidate_health_cache"), \
             patch("app.api.endpoints.health.storage_service", mock_storage):
            response = await client.delete(
                f"/api/v1/health/events/{event_id}",
                headers=auth_headers,
            )

        assert response.status_code == 204

        # Verify both photos were deleted from storage
        assert mock_storage.delete_image.call_count == 2

    @pytest.mark.asyncio
    async def test_delete_event_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 if event doesn't exist."""
        event_id = str(uuid4())

        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[event_result])

        response = await client.delete(
            f"/api/v1/health/events/{event_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404


# ============== Search Health Events Tests ==============

class TestSearchHealthEvents:
    """Tests for GET /api/v1/health/pet/{pet_id}/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_events_by_notes(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should search events by keyword in notes."""
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_category = create_mock_category(category_id=category_id, org_id=test_family_id)
        mock_event = create_mock_event(
            pet_id=pet_id,
            category_id=category_id,
            notes="Threw up after eating grass",
        )

        # Mock queries
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                categories_result,
                events_result,
            ]
        )

        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/search?q=grass",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert "grass" in data["events"][0]["event"]["notes"]

    @pytest.mark.asyncio
    async def test_search_events_by_category(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should search events by category name."""
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_category = create_mock_category(
            category_id=category_id,
            org_id=test_family_id,
            name="Vomiting",
            name_normalized="vomiting",
        )
        mock_event = create_mock_event(
            pet_id=pet_id,
            category_id=category_id,
        )

        # Mock queries
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result, pet_result, rls_result2, membership_result,
                categories_result,
                events_result,
            ]
        )

        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/search?q=vomit",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1

    @pytest.mark.asyncio
    async def test_search_events_validation_missing_query(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 if search query is missing."""
        pet_id = str(uuid4())

        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/search",
            headers=auth_headers,
        )

        assert response.status_code == 422  # Pydantic validation error


# ============== Upload Photo Tests ==============

class TestUploadHealthEventPhoto:
    """Tests for POST /api/v1/health/events/{event_id}/photo endpoint."""

    @pytest.mark.asyncio
    async def test_upload_photo_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should upload photo and create photo record."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())
        photo_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_photo = create_mock_photo(
            photo_id=photo_id,
            event_id=event_id,
            photo_url="https://example.com/photo.jpg",
        )

        # Mock verify_health_event_access
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Photo count query (0 existing photos)
        photo_count_result = MagicMock()
        photo_count_result.scalar.return_value = 0

        # Get pet for org_id
        pet_query_result = MagicMock()
        pet_query_result.scalar_one.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                photo_count_result,
                pet_query_result,
            ]
        )
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, 'id', UUID(photo_id)))

        # Mock storage service
        mock_storage = AsyncMock()
        mock_storage.upload_image.return_value = "https://example.com/photo.jpg"

        # Mock file upload
        from io import BytesIO
        file_content = b"fake image content"
        files = {"file": ("test.jpg", BytesIO(file_content), "image/jpeg")}

        with patch("app.api.endpoints.health.invalidate_health_cache"), \
             patch("app.api.endpoints.health.storage_service", mock_storage):
            response = await client.post(
                f"/api/v1/health/events/{event_id}/photo",
                files=files,
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["photo_url"] == "https://example.com/photo.jpg"
        assert data["sort_order"] == 0

    @pytest.mark.asyncio
    async def test_upload_photo_exceeds_limit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when exceeding photo limit (max 3)."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Mock access checks
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Photo count query (3 existing photos - at limit)
        photo_count_result = MagicMock()
        photo_count_result.scalar.return_value = 3

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                photo_count_result,
            ]
        )

        # Mock file upload
        from io import BytesIO
        files = {"file": ("test.jpg", BytesIO(b"fake"), "image/jpeg")}

        response = await client.post(
            f"/api/v1/health/events/{event_id}/photo",
            files=files,
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "Maximum 3 photos" in response.json()["detail"]


# ============== Delete Photo Tests ==============

class TestDeleteHealthEventPhoto:
    """Tests for DELETE /api/v1/health/events/{event_id}/photos/{photo_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_photo_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete photo from DB and R2."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())
        photo_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_photo = create_mock_photo(
            photo_id=photo_id,
            event_id=event_id,
            photo_url="https://example.com/photo.jpg",
        )

        # Mock verify_health_event_access
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Photo query
        photo_result = MagicMock()
        photo_result.scalar_one_or_none.return_value = mock_photo

        # Get pet for cache invalidation
        pet_query_result = MagicMock()
        pet_query_result.scalar_one.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                photo_result,
                pet_query_result,
            ]
        )
        mock_db_session.delete = AsyncMock()
        mock_db_session.commit = AsyncMock()

        # Mock storage service
        mock_storage = AsyncMock()
        mock_storage.delete_image.return_value = True

        with patch("app.api.endpoints.health.invalidate_health_cache"), \
             patch("app.api.endpoints.health.storage_service", mock_storage):
            response = await client.delete(
                f"/api/v1/health/events/{event_id}/photos/{photo_id}",
                headers=auth_headers,
            )

        assert response.status_code == 204

        # Verify photo deleted from storage
        mock_storage.delete_image.assert_called_once_with("https://example.com/photo.jpg")

    @pytest.mark.asyncio
    async def test_delete_photo_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 if photo doesn't exist."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())
        photo_id = str(uuid4())

        mock_event = create_mock_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        # Mock access checks
        event_lookup = MagicMock()
        event_lookup.scalar_one_or_none.return_value = mock_event

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Photo not found
        photo_result = MagicMock()
        photo_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_lookup,
                rls_result, pet_result, rls_result2, membership_result,
                photo_result,
            ]
        )

        response = await client.delete(
            f"/api/v1/health/events/{event_id}/photos/{photo_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Photo not found" in response.json()["detail"]


# ============== Authorization Tests ==============

class TestHealthAuthorization:
    """Tests for authorization across all health endpoints."""

    @pytest.mark.asyncio
    async def test_all_endpoints_require_auth(
        self,
        client: AsyncClient,
    ):
        """Should return 401 for all endpoints without auth token."""
        pet_id = str(uuid4())
        event_id = str(uuid4())
        photo_id = str(uuid4())

        endpoints = [
            ("GET", f"/api/v1/health/pet/{pet_id}/categories"),
            ("POST", f"/api/v1/health/pet/{pet_id}/events"),
            ("GET", f"/api/v1/health/pet/{pet_id}/events"),
            ("GET", f"/api/v1/health/pet/{pet_id}/search?q=test"),
            ("GET", f"/api/v1/health/events/{event_id}"),
            ("PATCH", f"/api/v1/health/events/{event_id}"),
            ("DELETE", f"/api/v1/health/events/{event_id}"),
            ("DELETE", f"/api/v1/health/events/{event_id}/photos/{photo_id}"),
        ]

        for method, url in endpoints:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json={})
            elif method == "PATCH":
                response = await client.patch(url, json={})
            elif method == "DELETE":
                response = await client.delete(url)

            assert response.status_code == 401, f"Failed for {method} {url}"
