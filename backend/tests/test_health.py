"""
Comprehensive integration tests for health event endpoints.

Tests cover:
- GET /api/v1/health/pet/{pet_id}/categories - list categories
- POST /api/v1/health/pet/{pet_id}/events - create event
- GET /api/v1/health/pet/{pet_id}/events - list events
- GET /api/v1/health/pet/{pet_id}/search - search events
- GET /api/v1/health/events/{event_id} - get single event
- PATCH /api/v1/health/events/{event_id} - update event
- DELETE /api/v1/health/events/{event_id} - delete event
- POST /api/v1/health/events/{event_id}/photo - upload photo
- DELETE /api/v1/health/events/{event_id}/photos/{photo_id} - delete photo
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
    create_mock_pet,
)


# Helper functions to create mock health objects
def create_mock_category(
    category_id: str = None,
    org_id: str = None,
    name: str = "Vomit",
    created_by: str = None,
):
    """Create a mock PetHealthCategory object."""
    from uuid import UUID
    category = MagicMock()
    # Ensure we always have valid UUID strings
    if category_id:
        category.id = UUID(category_id) if isinstance(category_id, str) else category_id
    else:
        category.id = uuid4()

    if org_id:
        category.org_id = UUID(org_id) if isinstance(org_id, str) else org_id
    else:
        category.org_id = uuid4()

    category.name = name
    category.name_normalized = name.lower().strip()

    if created_by:
        category.created_by = UUID(created_by) if isinstance(created_by, str) else created_by
    else:
        category.created_by = None

    category.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return category


def create_mock_health_event(
    event_id: str = None,
    pet_id: str = None,
    category_id: str = None,
    occurred_at: datetime = None,
    notes: str = None,
    created_by: str = None,
):
    """Create a mock PetHealthEvent object."""
    from uuid import UUID
    event = MagicMock()

    # Ensure we always have valid UUID objects
    if event_id:
        event.id = UUID(event_id) if isinstance(event_id, str) else event_id
    else:
        event.id = uuid4()

    if pet_id:
        event.pet_id = UUID(pet_id) if isinstance(pet_id, str) else pet_id
    else:
        event.pet_id = uuid4()

    if category_id:
        event.category_id = UUID(category_id) if isinstance(category_id, str) else category_id
    else:
        event.category_id = uuid4()

    event.occurred_at = occurred_at or datetime.now(timezone.utc).replace(tzinfo=None)
    event.notes = notes

    if created_by:
        event.created_by = UUID(created_by) if isinstance(created_by, str) else created_by
    else:
        event.created_by = None

    event.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    event.photos = []  # Default to no photos
    return event


def create_mock_health_event_photo(
    photo_id: str = None,
    event_id: str = None,
    photo_url: str = "https://example.com/photo.jpg",
    sort_order: int = 0,
):
    """Create a mock PetHealthEventPhoto object."""
    from uuid import UUID
    photo = MagicMock()

    if photo_id:
        photo.id = UUID(photo_id) if isinstance(photo_id, str) else photo_id
    else:
        photo.id = uuid4()

    if event_id:
        photo.event_id = UUID(event_id) if isinstance(event_id, str) else event_id
    else:
        photo.event_id = uuid4()

    photo.photo_url = photo_url
    photo.sort_order = sort_order
    photo.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    return photo


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
        """Should list all health categories for a pet's family."""
        pet_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )

        mock_category_1 = create_mock_category(
            org_id=test_family_id, name="Vomit", created_by=test_user_id
        )
        mock_category_2 = create_mock_category(
            org_id=test_family_id, name="Diarrhea", created_by=test_user_id
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [
            mock_category_1,
            mock_category_2,
        ]

        mock_db_session.execute = AsyncMock(
            side_effect=[pet_result, membership_result, categories_result]
        )

        # Mock cache miss
        with patch("app.api.endpoints.health.cache_get", return_value=None):
            with patch("app.api.endpoints.health.cache_set"):
                # Make request
                response = await client.get(
                    f"/api/v1/health/pet/{pet_id}/categories",
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Vomit"
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

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[pet_result, membership_result, categories_result]
        )

        # Mock cache miss
        with patch("app.api.endpoints.health.cache_get", return_value=None):
            with patch("app.api.endpoints.health.cache_set"):
                # Make request
                response = await client.get(
                    f"/api/v1/health/pet/{pet_id}/categories",
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_list_categories_pet_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when pet does not exist."""
        pet_id = str(uuid4())

        # Mock pet not found
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=pet_result)

        # Make request
        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/categories",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 404
        assert "Pet not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_categories_unauthorized(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 403 when user does not have access to pet."""
        pet_id = str(uuid4())

        # Setup mocks - pet exists but user not in family
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # No membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[pet_result, membership_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/categories",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]


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
        """Should create a health event with category."""
        pet_id = str(uuid4())
        event_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(
            pet_id=pet_id, org_id=test_family_id, name="Buddy"
        )
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            org_id=test_family_id, name="Vomit", created_by=test_user_id
        )
        mock_event = create_mock_health_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=str(mock_category.id),
            notes="Had breakfast vomit",
            created_by=test_user_id,
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        event_result = MagicMock()
        event_result.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                pet_result,
                membership_result,
                category_result,  # get_or_create_category
                event_result,  # reload event with photos
            ]
        )

        # Mock cache invalidation
        with patch("app.api.endpoints.health.invalidate_health_cache"):
            with patch("app.api.endpoints.health.notify_family_health_event"):
                # Make request
                response = await client.post(
                    f"/api/v1/health/pet/{pet_id}/events",
                    json={
                        "category_name": "Vomit",
                        "notes": "Had breakfast vomit",
                        "notify_family": False,
                    },
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == event_id
        assert data["category_id"] == str(mock_category.id)
        assert data["notes"] == "Had breakfast vomit"
        assert data["photos"] == []

    @pytest.mark.asyncio
    async def test_create_event_with_custom_timestamp(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create event with custom occurred_at timestamp."""
        pet_id = str(uuid4())
        event_id = str(uuid4())
        custom_time = datetime.now(timezone.utc) - timedelta(hours=2)

        # Setup mocks
        mock_pet = create_mock_pet(
            pet_id=pet_id, org_id=test_family_id, name="Luna"
        )
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            org_id=test_family_id, name="Sneeze", created_by=test_user_id
        )
        mock_event = create_mock_health_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=str(mock_category.id),
            occurred_at=custom_time.replace(tzinfo=None),
            created_by=test_user_id,
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        event_result = MagicMock()
        event_result.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[pet_result, membership_result, category_result, event_result]
        )

        # Mock cache invalidation
        with patch("app.api.endpoints.health.invalidate_health_cache"):
            with patch("app.api.endpoints.health.notify_family_health_event"):
                # Make request
                response = await client.post(
                    f"/api/v1/health/pet/{pet_id}/events",
                    json={
                        "category_name": "Sneeze",
                        "occurred_at": custom_time.isoformat(),
                    },
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_event_future_date_rejected(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should reject event with future timestamp."""
        pet_id = str(uuid4())
        future_time = datetime.now(timezone.utc) + timedelta(days=1)

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[pet_result, membership_result]
        )

        # Make request
        response = await client.post(
            f"/api/v1/health/pet/{pet_id}/events",
            json={
                "category_name": "Vomit",
                "occurred_at": future_time.isoformat(),
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 400
        assert "cannot be in the future" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_event_validation_error(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 422 for invalid request payload."""
        pet_id = str(uuid4())

        # Make request with missing required field
        response = await client.post(
            f"/api/v1/health/pet/{pet_id}/events",
            json={
                # Missing category_name
                "notes": "Some notes",
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_event_unauthorized(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should return 401 when no auth token provided."""
        pet_id = str(uuid4())

        # Make request without auth headers
        response = await client.post(
            f"/api/v1/health/pet/{pet_id}/events",
            json={"category_name": "Vomit"},
        )

        # Verify response
        assert response.status_code == 401


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

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Vomit"
        )
        mock_event = create_mock_health_event(
            pet_id=pet_id,
            category_id=category_id,
            notes="Morning vomit",
            created_by=test_user_id,
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                pet_result,
                membership_result,
                categories_result,
                events_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.health.cache_get", return_value=None):
            with patch("app.api.endpoints.health.cache_set"):
                # Make request
                response = await client.get(
                    f"/api/v1/health/pet/{pet_id}/events",
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["event"]["notes"] == "Morning vomit"
        assert data["events"][0]["category"]["name"] == "Vomit"

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

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Vomiting"
        )
        mock_event = create_mock_health_event(
            pet_id=pet_id, category_id=category_id, created_by=test_user_id
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                pet_result,
                membership_result,
                categories_result,
                events_result,
            ]
        )

        # Make request with category filter (should match "vomit" in "Vomiting")
        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/events?category=vomit",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1

    @pytest.mark.asyncio
    async def test_list_events_with_date_range_filter(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should filter events by date range."""
        pet_id = str(uuid4())
        category_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Sneeze"
        )
        mock_event = create_mock_health_event(
            pet_id=pet_id,
            category_id=category_id,
            occurred_at=datetime.now(timezone.utc) - timedelta(days=1),
            created_by=test_user_id,
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                pet_result,
                membership_result,
                categories_result,
                events_result,
            ]
        )

        # Make request with date range
        since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        until = datetime.now(timezone.utc).isoformat()

        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/events?since={since}&until={until}",
            headers=auth_headers,
        )

        # Verify response
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

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Vomit"
        )
        mock_event = create_mock_health_event(
            pet_id=pet_id, category_id=category_id, created_by=test_user_id
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                pet_result,
                membership_result,
                categories_result,
                events_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.health.cache_get", return_value=None):
            with patch("app.api.endpoints.health.cache_set"):
                # Make request with pagination
                response = await client.get(
                    f"/api/v1/health/pet/{pet_id}/events?limit=10&offset=0",
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 200

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

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = []

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                pet_result,
                membership_result,
                categories_result,
                events_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.health.cache_get", return_value=None):
            with patch("app.api.endpoints.health.cache_set"):
                # Make request
                response = await client.get(
                    f"/api/v1/health/pet/{pet_id}/events",
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 0


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

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Vomit"
        )
        mock_event = create_mock_health_event(
            pet_id=pet_id,
            category_id=category_id,
            notes="Had breakfast before vomiting",
            created_by=test_user_id,
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                pet_result,
                membership_result,
                categories_result,
                events_result,
            ]
        )

        # Make request
        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/search?q=breakfast",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert "breakfast" in data["events"][0]["event"]["notes"]

    @pytest.mark.asyncio
    async def test_search_events_by_category_name(
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

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Diarrhea"
        )
        mock_event = create_mock_health_event(
            pet_id=pet_id, category_id=category_id, created_by=test_user_id
        )

        # Mock database queries
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        categories_result = MagicMock()
        categories_result.scalars.return_value.all.return_value = [mock_category]

        events_result = MagicMock()
        events_result.scalars.return_value.all.return_value = [mock_event]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                pet_result,
                membership_result,
                categories_result,
                events_result,
            ]
        )

        # Make request
        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/search?q=diarrhea",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1

    @pytest.mark.asyncio
    async def test_search_events_validation_error(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 422 when search query is missing."""
        pet_id = str(uuid4())

        # Make request without query parameter
        response = await client.get(
            f"/api/v1/health/pet/{pet_id}/search",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 422


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
        """Should return single health event with category."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Vomit"
        )
        mock_event = create_mock_health_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            notes="Had food vomit",
            created_by=test_user_id,
        )

        # Mock database queries
        event_result_1 = MagicMock()
        event_result_1.scalar_one_or_none.return_value = mock_event

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock the join query that returns both event and category
        event_category_result = MagicMock()
        event_category_result.one.return_value = (mock_event, mock_category)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result_1,
                pet_result,
                membership_result,
                event_category_result,
            ]
        )

        # Make request
        response = await client.get(
            f"/api/v1/health/events/{event_id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["event"]["id"] == event_id
        assert data["event"]["notes"] == "Had food vomit"
        assert data["category"]["name"] == "Vomit"

    @pytest.mark.asyncio
    async def test_get_event_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when event does not exist."""
        event_id = str(uuid4())

        # Mock event not found
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=event_result)

        # Make request
        response = await client.get(
            f"/api/v1/health/events/{event_id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 404
        assert "Health event not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_event_unauthorized(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 403 when user does not have access to event."""
        event_id = str(uuid4())
        pet_id = str(uuid4())

        # Setup mocks - event exists but user not in family
        mock_event = create_mock_health_event(event_id=event_id, pet_id=pet_id)
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)

        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # No membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[event_result, pet_result, membership_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/health/events/{event_id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]


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

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Vomit"
        )
        mock_event = create_mock_health_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            notes="Old notes",
            created_by=test_user_id,
        )

        # Mock database queries
        event_result_1 = MagicMock()
        event_result_1.scalar_one_or_none.return_value = mock_event

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        event_result_2 = MagicMock()
        event_result_2.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result_1,
                pet_result,
                membership_result,
                category_result,
                event_result_2,
            ]
        )

        # Mock cache invalidation
        with patch("app.api.endpoints.health.invalidate_health_cache"):
            # Make request
            response = await client.patch(
                f"/api/v1/health/events/{event_id}",
                json={"notes": "Updated notes"},
                headers=auth_headers,
            )

        # Verify response
        assert response.status_code == 200
        # Verify notes were updated on mock
        assert mock_event.notes == "Updated notes"

    @pytest.mark.asyncio
    async def test_update_event_category(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update event category."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        old_category_id = str(uuid4())
        new_category_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_old_category = create_mock_category(
            category_id=old_category_id, org_id=test_family_id, name="Vomit"
        )
        mock_new_category = create_mock_category(
            category_id=new_category_id, org_id=test_family_id, name="Diarrhea"
        )
        mock_event = create_mock_health_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=old_category_id,
            created_by=test_user_id,
        )

        # Mock database queries
        event_result_1 = MagicMock()
        event_result_1.scalar_one_or_none.return_value = mock_event

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        old_category_result = MagicMock()
        old_category_result.scalar_one.return_value = mock_old_category

        new_category_result = MagicMock()
        new_category_result.scalar_one.return_value = mock_new_category

        event_result_2 = MagicMock()
        event_result_2.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result_1,
                pet_result,
                membership_result,
                old_category_result,
                new_category_result,
                event_result_2,
            ]
        )

        # Mock cache invalidation and orphan cleanup
        with patch("app.api.endpoints.health.invalidate_health_cache"):
            with patch("app.api.endpoints.health.delete_orphaned_category"):
                # Make request
                response = await client.patch(
                    f"/api/v1/health/events/{event_id}",
                    json={"category_name": "Diarrhea"},
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_event_timestamp(
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
        new_time = datetime.now(timezone.utc) - timedelta(hours=3)

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_category = create_mock_category(
            category_id=category_id, org_id=test_family_id, name="Sneeze"
        )
        mock_event = create_mock_health_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            created_by=test_user_id,
        )

        # Mock database queries
        event_result_1 = MagicMock()
        event_result_1.scalar_one_or_none.return_value = mock_event

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        category_result = MagicMock()
        category_result.scalar_one.return_value = mock_category

        event_result_2 = MagicMock()
        event_result_2.scalar_one.return_value = mock_event

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result_1,
                pet_result,
                membership_result,
                category_result,
                event_result_2,
            ]
        )

        # Mock cache invalidation
        with patch("app.api.endpoints.health.invalidate_health_cache"):
            # Make request
            response = await client.patch(
                f"/api/v1/health/events/{event_id}",
                json={"occurred_at": new_time.isoformat()},
                headers=auth_headers,
            )

        # Verify response
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_event_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when event does not exist."""
        event_id = str(uuid4())

        # Mock event not found
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=event_result)

        # Make request
        response = await client.patch(
            f"/api/v1/health/events/{event_id}",
            json={"notes": "Updated notes"},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 404
        assert "Health event not found" in response.json()["detail"]


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
        """Should delete health event."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_event = create_mock_health_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            created_by=test_user_id,
        )

        # Mock database queries
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        pet_result_1 = MagicMock()
        pet_result_1.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        pet_result_2 = MagicMock()
        pet_result_2.scalar_one.return_value = mock_pet

        photos_result = MagicMock()
        photos_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result,
                pet_result_1,
                membership_result,
                pet_result_2,
                photos_result,
            ]
        )

        # Mock delete operation
        mock_db_session.delete = AsyncMock()

        # Mock cache invalidation and orphan cleanup
        with patch("app.api.endpoints.health.invalidate_health_cache"):
            with patch("app.api.endpoints.health.delete_orphaned_category"):
                # Make request
                response = await client.delete(
                    f"/api/v1/health/events/{event_id}",
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 204
        mock_db_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_event_with_photos(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete event and associated photos."""
        event_id = str(uuid4())
        pet_id = str(uuid4())
        category_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_event = create_mock_health_event(
            event_id=event_id,
            pet_id=pet_id,
            category_id=category_id,
            created_by=test_user_id,
        )
        mock_photo = create_mock_health_event_photo(event_id=event_id)

        # Mock database queries
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        pet_result_1 = MagicMock()
        pet_result_1.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        pet_result_2 = MagicMock()
        pet_result_2.scalar_one.return_value = mock_pet

        photos_result = MagicMock()
        photos_result.scalars.return_value.all.return_value = [mock_photo]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result,
                pet_result_1,
                membership_result,
                pet_result_2,
                photos_result,
            ]
        )

        # Mock delete operation
        mock_db_session.delete = AsyncMock()

        # Mock storage service
        with patch("app.api.endpoints.health.storage_service") as mock_storage:
            mock_storage.delete_image = AsyncMock(return_value=True)

            # Mock cache invalidation and orphan cleanup
            with patch("app.api.endpoints.health.invalidate_health_cache"):
                with patch("app.api.endpoints.health.delete_orphaned_category"):
                    # Make request
                    response = await client.delete(
                        f"/api/v1/health/events/{event_id}",
                        headers=auth_headers,
                    )

        # Verify response
        assert response.status_code == 204
        mock_db_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_event_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when event does not exist."""
        event_id = str(uuid4())

        # Mock event not found
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=event_result)

        # Make request
        response = await client.delete(
            f"/api/v1/health/events/{event_id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 404
        assert "Health event not found" in response.json()["detail"]


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
        """Should upload photo to health event."""
        event_id = str(uuid4())
        pet_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_event = create_mock_health_event(event_id=event_id, pet_id=pet_id)
        mock_photo = create_mock_health_event_photo(event_id=event_id)

        # Mock database queries
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        pet_result_1 = MagicMock()
        pet_result_1.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        photo_count_result = MagicMock()
        photo_count_result.scalar.return_value = 0

        pet_result_2 = MagicMock()
        pet_result_2.scalar_one.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result,
                pet_result_1,
                membership_result,
                photo_count_result,
                pet_result_2,
            ]
        )

        # Mock refresh to set photo ID
        async def mock_refresh(obj):
            obj.id = mock_photo.id

        mock_db_session.refresh = mock_refresh

        # Mock storage service
        with patch("app.api.endpoints.health.storage_service") as mock_storage:
            mock_storage.upload_image = AsyncMock(
                return_value="https://example.com/photo.jpg"
            )

            # Mock cache invalidation
            with patch("app.api.endpoints.health.invalidate_health_cache"):
                # Make request with file
                files = {"file": ("test.jpg", b"fake image data", "image/jpeg")}
                response = await client.post(
                    f"/api/v1/health/events/{event_id}/photo",
                    files=files,
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["photo_url"] == "https://example.com/photo.jpg"

    @pytest.mark.asyncio
    async def test_upload_photo_max_limit_exceeded(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should reject upload when max 3 photos already exist."""
        event_id = str(uuid4())
        pet_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_event = create_mock_health_event(event_id=event_id, pet_id=pet_id)

        # Mock database queries
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock photo count = 3 (max limit)
        photo_count_result = MagicMock()
        photo_count_result.scalar.return_value = 3

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result,
                pet_result,
                membership_result,
                photo_count_result,
            ]
        )

        # Make request
        files = {"file": ("test.jpg", b"fake image data", "image/jpeg")}
        response = await client.post(
            f"/api/v1/health/events/{event_id}/photo",
            files=files,
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 400
        assert "Maximum 3 photos" in response.json()["detail"]


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
        """Should delete photo from health event."""
        event_id = str(uuid4())
        photo_id = str(uuid4())
        pet_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_event = create_mock_health_event(event_id=event_id, pet_id=pet_id)
        mock_photo = create_mock_health_event_photo(
            photo_id=photo_id, event_id=event_id
        )

        # Mock database queries
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        pet_result_1 = MagicMock()
        pet_result_1.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        photo_result = MagicMock()
        photo_result.scalar_one_or_none.return_value = mock_photo

        pet_result_2 = MagicMock()
        pet_result_2.scalar_one.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=[
                event_result,
                pet_result_1,
                membership_result,
                photo_result,
                pet_result_2,
            ]
        )

        # Mock delete operation
        mock_db_session.delete = AsyncMock()

        # Mock storage service
        with patch("app.api.endpoints.health.storage_service") as mock_storage:
            mock_storage.delete_image = AsyncMock(return_value=True)

            # Mock cache invalidation
            with patch("app.api.endpoints.health.invalidate_health_cache"):
                # Make request
                response = await client.delete(
                    f"/api/v1/health/events/{event_id}/photos/{photo_id}",
                    headers=auth_headers,
                )

        # Verify response
        assert response.status_code == 204
        mock_db_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_photo_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 when photo does not exist."""
        event_id = str(uuid4())
        photo_id = str(uuid4())
        pet_id = str(uuid4())

        # Setup mocks
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id, family_id=test_family_id
        )
        mock_event = create_mock_health_event(event_id=event_id, pet_id=pet_id)

        # Mock database queries
        event_result = MagicMock()
        event_result.scalar_one_or_none.return_value = mock_event

        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Photo not found
        photo_result = MagicMock()
        photo_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[event_result, pet_result, membership_result, photo_result]
        )

        # Make request
        response = await client.delete(
            f"/api/v1/health/events/{event_id}/photos/{photo_id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 404
        assert "Photo not found" in response.json()["detail"]
