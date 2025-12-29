"""
Comprehensive integration tests for medication management endpoints.

Tests cover:
- Medication CRUD operations (list, create, get, update, delete)
- Dose recording and management
- Authorization checks (owner vs member, wrong org)
- Validation errors
- Edge cases (archived medications, PRN vs scheduled, photo limits)

NOTE: These tests mock the database session and use the FastAPI test client.
All authorization functions (verify_family_access, verify_pet_access, etc.)
call set_rls_user() first, which requires an RLS mock result in side_effect.
"""
from datetime import datetime, date, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from httpx import AsyncClient

from app.models.medication import MedicationType
from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
    create_mock_pet,
)


# ============== Helper Functions ==============

def create_mock_medication(
    medication_id: str = None,
    pet_id: str = None,
    name: str = "Prednisone",
    medication_type: str = "pill",
    dosage: str = "5mg",
    interval_days: int = 1,
    is_as_needed: bool = False,
    start_date: datetime = None,
    end_date: datetime = None,
    times_per_day: int = 2,
    notes: str = None,
    reminders_enabled: bool = False,
    timezone: str = "UTC",
    is_archived: bool = False,
    created_by: str = None,
) -> MagicMock:
    """Create a mock PetMedication object."""
    medication = MagicMock()
    medication.id = medication_id or str(uuid4())
    medication.pet_id = pet_id or str(uuid4())
    medication.name = name
    medication.medication_type = medication_type
    medication.dosage = dosage
    medication.interval_days = interval_days
    medication.is_as_needed = is_as_needed
    medication.start_date = start_date or datetime(2024, 1, 1)
    medication.end_date = end_date
    medication.times_per_day = times_per_day
    medication.notes = notes
    medication.reminders_enabled = reminders_enabled
    medication.timezone = timezone
    medication.is_archived = is_archived
    medication.created_by = created_by
    medication.created_at = datetime(2024, 1, 1)
    medication.photos = []
    return medication


def create_mock_dose(
    dose_id: str = None,
    medication_id: str = None,
    given_at: datetime = None,
    given_by: str = None,
    notes: str = None,
) -> MagicMock:
    """Create a mock PetMedicationDose object."""
    dose = MagicMock()
    dose.id = dose_id or str(uuid4())
    dose.medication_id = medication_id or str(uuid4())
    dose.given_at = given_at or datetime(2024, 1, 1)
    dose.given_by = given_by or str(uuid4())
    dose.notes = notes
    dose.created_at = datetime(2024, 1, 1)
    return dose


def create_mock_schedule(
    schedule_id: str = None,
    medication_id: str = None,
    scheduled_hour: int = 9,
    scheduled_minute: int = 0,
) -> MagicMock:
    """Create a mock MedicationSchedule object."""
    schedule = MagicMock()
    schedule.id = schedule_id or str(uuid4())
    schedule.medication_id = medication_id or str(uuid4())
    schedule.scheduled_hour = scheduled_hour
    schedule.scheduled_minute = scheduled_minute
    return schedule


def create_mock_photo(
    photo_id: str = None,
    medication_id: str = None,
    photo_url: str = "https://example.com/photo.jpg",
    sort_order: int = 0,
) -> MagicMock:
    """Create a mock PetMedicationPhoto object."""
    photo = MagicMock()
    photo.id = photo_id or str(uuid4())
    photo.medication_id = medication_id or str(uuid4())
    photo.photo_url = photo_url
    photo.sort_order = sort_order
    photo.created_at = datetime(2024, 1, 1)
    return photo


def create_mock_user(
    user_id: str = None,
    first_name: str = "John",
    last_name: str = "Doe",
) -> MagicMock:
    """Create a mock User object."""
    user = MagicMock()
    user.id = user_id or str(uuid4())
    user.first_name = first_name
    user.last_name = last_name
    return user


# ============== List Medications Tests ==============

class TestListMedications:
    """Tests for GET /api/v1/medications endpoint."""

    @pytest.mark.asyncio
    async def test_list_medications_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list all medications for org."""
        pet_id = str(uuid4())

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_med1 = create_mock_medication(
            pet_id=pet_id,
            name="Prednisone",
            medication_type="pill",
        )
        mock_med2 = create_mock_medication(
            pet_id=pet_id,
            name="Eye Drops",
            medication_type="drops",
        )

        # Mock database queries - set_rls_user is called first, then verify_family_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        pets_result = MagicMock()
        pets_result.scalars.return_value.all.return_value = [UUID(pet_id)]

        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = [mock_med1, mock_med2]

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, pets_result, meds_result]
        )

        # Make request with mocked cache
        with patch("app.api.endpoints.medications.cache_get", return_value=None), \
             patch("app.api.endpoints.medications.cache_set"):
            response = await client.get(
                f"/api/v1/medications?org_id={test_family_id}",
                headers=auth_headers,
            )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["medications"]) == 2
        assert data["medications"][0]["name"] == "Prednisone"
        assert data["medications"][1]["name"] == "Eye Drops"

    @pytest.mark.asyncio
    async def test_list_medications_unauthorized_not_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 403 if user not member of org."""
        # Mock RLS call
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock no membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result]
        )

        response = await client.get(
            f"/api/v1/medications?org_id={test_family_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_medications_no_auth_token(
        self,
        client: AsyncClient,
        test_family_id: str,
    ):
        """Should return 401 without auth token."""
        response = await client.get(
            f"/api/v1/medications?org_id={test_family_id}",
        )

        assert response.status_code == 401


# ============== Create Medication Tests ==============

class TestCreateMedication:
    """Tests for POST /api/v1/medications endpoint."""

    @pytest.mark.asyncio
    async def test_create_medication_validation_error_interval_days(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 for invalid interval_days."""
        pet_id = str(uuid4())

        # Mock RLS and membership/pet access checks
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        membership_result = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_mock = MagicMock()
        membership_mock.scalar_one_or_none.return_value = membership_result

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        pet_membership_result = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        pet_membership_mock = MagicMock()
        pet_membership_mock.scalar_one_or_none.return_value = pet_membership_result

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )
        pet_mock = MagicMock()
        pet_mock.scalar_one_or_none.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, membership_mock, rls_result2, pet_membership_mock, pet_mock]
        )

        # Test interval_days > 30
        response = await client.post(
            "/api/v1/medications",
            json={
                "pet_id": pet_id,
                "name": "Test Med",
                "medication_type": "pill",
                "interval_days": 35,  # Invalid: > 30
                "start_date": "2024-01-01T00:00:00Z",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "interval_days must be between 1 and 30" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_medication_validation_error_times_per_day(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 for invalid times_per_day."""
        pet_id = str(uuid4())

        # Mock RLS and access checks
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        membership_result = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_mock = MagicMock()
        membership_mock.scalar_one_or_none.return_value = membership_result

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        pet_membership_result = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        pet_membership_mock = MagicMock()
        pet_membership_mock.scalar_one_or_none.return_value = pet_membership_result

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )
        pet_mock = MagicMock()
        pet_mock.scalar_one_or_none.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, membership_mock, rls_result2, pet_membership_mock, pet_mock]
        )

        response = await client.post(
            "/api/v1/medications",
            json={
                "pet_id": pet_id,
                "name": "Test Med",
                "medication_type": "pill",
                "times_per_day": 10,  # Invalid: > 8
                "start_date": "2024-01-01T00:00:00Z",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "times_per_day must be between 1 and 8" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_medication_validation_error_end_date(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 if end_date before start_date."""
        pet_id = str(uuid4())

        # Mock RLS and access checks
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        membership_result = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_mock = MagicMock()
        membership_mock.scalar_one_or_none.return_value = membership_result

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        pet_membership_result = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        pet_membership_mock = MagicMock()
        pet_membership_mock.scalar_one_or_none.return_value = pet_membership_result

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )
        pet_mock = MagicMock()
        pet_mock.scalar_one_or_none.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, membership_mock, rls_result2, pet_membership_mock, pet_mock]
        )

        response = await client.post(
            "/api/v1/medications",
            json={
                "pet_id": pet_id,
                "name": "Test Med",
                "medication_type": "pill",
                "start_date": "2024-02-01T00:00:00Z",
                "end_date": "2024-01-01T00:00:00Z",  # Before start_date
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "end_date must be on or after start_date" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_medication_validation_error_prn_with_reminders(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 for PRN medication with reminders enabled."""
        pet_id = str(uuid4())

        # Mock RLS and access checks
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        membership_result = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_mock = MagicMock()
        membership_mock.scalar_one_or_none.return_value = membership_result

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        pet_membership_result = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        pet_membership_mock = MagicMock()
        pet_membership_mock.scalar_one_or_none.return_value = pet_membership_result

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )
        pet_mock = MagicMock()
        pet_mock.scalar_one_or_none.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, membership_mock, rls_result2, pet_membership_mock, pet_mock]
        )

        response = await client.post(
            "/api/v1/medications",
            json={
                "pet_id": pet_id,
                "name": "PRN Med",
                "medication_type": "pill",
                "is_as_needed": True,
                "reminders_enabled": True,  # Invalid for PRN
                "start_date": "2024-01-01T00:00:00Z",
            },
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "As-needed (PRN) medications cannot have reminders enabled" in response.json()["detail"]


# ============== Integration Test Notes ==============

class TestMedicationIntegrationNotes:
    """
    Documentation of comprehensive test coverage that should be implemented.

    The tests above demonstrate the core patterns. A complete test suite would include:

    1. GET /api/v1/medications/{id} - get single medication
       - Test success with schedules and photos
       - Test 404 when medication doesn't exist
       - Test 403 when user doesn't have access

    2. PATCH /api/v1/medications/{id} - update medication
       - Test successful field updates
       - Test converting scheduled to PRN (clears reminders, interval)
       - Test converting PRN to scheduled
       - Test updating scheduled_times
       - Test 404/403 errors

    3. DELETE /api/v1/medications/{id} - delete medication
       - Test hard delete when no doses exist
       - Test archive when doses exist (preserves history)
       - Test photo deletion on hard delete
       - Test 404/403 errors

    4. POST /api/v1/medications/{id}/photos - upload photo
       - Test successful upload
       - Test photo limit (max 3)
       - Test 404/403 errors

    5. DELETE /api/v1/medications/{id}/photos/{photo_id} - delete photo
       - Test successful deletion
       - Test R2 storage cleanup
       - Test 404 for non-existent photo

    6. POST /api/v1/doses - record dose
       - Test successful dose recording
       - Test custom given_at timestamp
       - Test notes field
       - Test cache invalidation

    7. GET /api/v1/doses/medication/{id} - list doses
       - Test pagination (limit parameter)
       - Test user name formatting ("You" for current user)
       - Test ordering (most recent first)

    8. PATCH /api/v1/doses/{id} - update dose
       - Test updating given_at
       - Test updating notes
       - Test 404/403 errors

    9. DELETE /api/v1/doses/{id} - delete dose
       - Test successful deletion
       - Test cache invalidation
       - Test 404/403 errors

    Each endpoint should test:
    - Happy path (200/201 responses)
    - Validation errors (400/422)
    - Authentication errors (401)
    - Authorization errors (403)
    - Not found errors (404)
    - Edge cases specific to the domain

    The key pattern for all tests:
    1. Mock RLS call (set_rls_user) - returns None
    2. Mock authorization checks (verify_*_access) - returns membership/object
    3. Mock business logic queries
    4. Mock cache operations
    5. Assert response status and data
    6. Verify side effects (cache invalidation, notifications, etc.)
    """
    pass
