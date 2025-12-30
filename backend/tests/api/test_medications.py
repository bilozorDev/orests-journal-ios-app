"""
Comprehensive integration tests for medication management endpoints.

Tests cover:
- Medication CRUD operations (list, create, get, update, delete)
- Dose recording and management
- Authorization checks (owner vs member, wrong org)
- Validation errors
- Edge cases (archived medications, PRN vs scheduled, photo limits)

IMPORTANT: Authorization Mock Patterns
======================================

These tests mock the database session and use the FastAPI test client.

Different endpoints use different authorization functions with nested calls:

1. verify_family_access (e.g., list medications):
   - Set RLS
   - Query for membership

2. verify_pet_access (e.g., create medication):
   - Set RLS
   - Query for pet
   - Call verify_family_access (see above)

3. verify_medication_access (e.g., get/update/delete medication, upload photo):
   - Query for medication
   - Call verify_pet_access (see above)

4. verify_dose_access (e.g., update/delete dose):
   - Query for dose
   - Call verify_medication_access (see above)

Helper Functions
================

Use these helper functions to generate the correct mock sequence:

- setup_medication_access_mocks(medication, pet, membership)
  Returns list of 5 mocks for verify_medication_access flow

- setup_dose_access_mocks(dose, medication, pet, membership)
  Returns list of 6 mocks for verify_dose_access flow

Example Usage
=============

auth_mocks = setup_medication_access_mocks(
    mock_medication, mock_pet, mock_membership
)

# Add any business logic mocks after authorization
business_logic_mocks = [result1, result2, ...]

mock_db_session.execute = AsyncMock(
    side_effect=auth_mocks + business_logic_mocks
)

Note: Tests that need updating will have a NOTE comment explaining the required changes.
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

def setup_medication_access_mocks(
    medication: MagicMock,
    pet: MagicMock,
    membership: MagicMock,
) -> list:
    """
    Create the correct sequence of mock results for verify_medication_access.

    The authorization flow is:
    1. Query medication by ID
    2. If found, call verify_pet_access which:
       a. Set RLS
       b. Query for pet
       c. If found, call verify_family_access which:
          i. Set RLS
          ii. Query for membership

    Returns list of mock results in the correct order for side_effect.
    """
    # 1. Get medication
    med_query_result = MagicMock()
    med_query_result.scalar_one_or_none.return_value = medication

    # 2. verify_pet_access: set RLS
    rls_result1 = MagicMock()
    rls_result1.scalar_one_or_none.return_value = None

    # 3. verify_pet_access: get pet
    pet_result = MagicMock()
    pet_result.scalar_one_or_none.return_value = pet

    # 4. verify_family_access: set RLS
    rls_result2 = MagicMock()
    rls_result2.scalar_one_or_none.return_value = None

    # 5. verify_family_access: get membership
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership

    return [
        med_query_result,
        rls_result1,
        pet_result,
        rls_result2,
        membership_result,
    ]


def setup_dose_access_mocks(
    dose: MagicMock,
    medication: MagicMock,
    pet: MagicMock,
    membership: MagicMock,
) -> list:
    """
    Create the correct sequence of mock results for verify_dose_access.

    The authorization flow is:
    1. Query dose by ID
    2. If found, call verify_medication_access (see above)

    Returns list of mock results in the correct order for side_effect.
    """
    # 1. Get dose
    dose_query_result = MagicMock()
    dose_query_result.scalar_one_or_none.return_value = dose

    # 2-6. verify_medication_access flow
    medication_access_mocks = setup_medication_access_mocks(
        medication, pet, membership
    )

    return [dose_query_result] + medication_access_mocks


def create_mock_medication(
    medication_id: str = None,
    pet_id: str = None,
    name: str = "Prednisone",
    friendly_name: str = None,
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
    medication.friendly_name = friendly_name
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

        # Mock scheduled times query (returns empty list)
        schedules_result = MagicMock()
        schedules_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, pets_result, meds_result, schedules_result]
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
        # Verify scheduled_times is included in response
        assert "scheduled_times" in data["medications"][0]
        assert "scheduled_times" in data["medications"][1]

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


# ============== Get Single Medication Tests ==============

class TestGetMedication:
    """Tests for GET /api/v1/medications/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_medication_success_with_schedules_and_photos(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return medication with schedules and photos."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Create mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
            name="Prednisone",
            reminders_enabled=True,
        )
        mock_schedule1 = create_mock_schedule(
            medication_id=medication_id, scheduled_hour=9, scheduled_minute=0
        )
        mock_schedule2 = create_mock_schedule(
            medication_id=medication_id, scheduled_hour=21, scheduled_minute=0
        )
        mock_photo1 = create_mock_photo(medication_id=medication_id, sort_order=0)
        mock_medication.photos = [mock_photo1]

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Mock business logic queries
        # Get medication with photos
        med_with_photos_result = MagicMock()
        med_with_photos_result.scalar_one.return_value = mock_medication

        # Get schedules
        schedules_result = MagicMock()
        schedules_result.scalars.return_value.all.return_value = [
            mock_schedule1,
            mock_schedule2,
        ]

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [med_with_photos_result, schedules_result]
        )

        response = await client.get(
            f"/api/v1/medications/{medication_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == medication_id
        assert data["name"] == "Prednisone"
        assert len(data["scheduled_times"]) == 2
        assert len(data["photos"]) == 1

    @pytest.mark.asyncio
    async def test_get_medication_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 when medication doesn't exist."""
        medication_id = str(uuid4())

        # Mock RLS
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock membership check
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Mock pet query (returns None - pet not found via medication)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, pet_result]
        )

        response = await client.get(
            f"/api/v1/medications/{medication_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_medication_forbidden_wrong_org(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 403 when user doesn't have access to medication."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        wrong_org_id = str(uuid4())

        # Create mocks - medication exists but in different org
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=wrong_org_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )

        # 1. Get medication
        med_query_result = MagicMock()
        med_query_result.scalar_one_or_none.return_value = mock_medication

        # 2. verify_pet_access: set RLS
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # 3. verify_pet_access: get pet
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # 4. verify_family_access: set RLS
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # 5. verify_family_access: no membership found (403)
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[
                med_query_result,
                rls_result1,
                pet_result,
                rls_result2,
                membership_result,
            ]
        )

        response = await client.get(
            f"/api/v1/medications/{medication_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403


# ============== Update Medication Tests ==============

class TestUpdateMedication:
    """Tests for PATCH /api/v1/medications/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_medication_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully update medication fields."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id, name="Buddy")
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
            name="Old Name",
            dosage="5mg",
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic mocks
        # Get pet for cache invalidation
        pet_result2 = MagicMock()
        pet_result2.scalar_one.return_value = mock_pet

        # For fetching existing schedules
        schedules_result = MagicMock()
        schedules_result.scalars.return_value.all.return_value = []

        # For re-fetching medication with photos
        med_with_photos_result = MagicMock()
        med_with_photos_result.scalar_one.return_value = mock_medication

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                pet_result2,
                schedules_result,
                med_with_photos_result,
            ]
        )

        with patch("app.api.endpoints.medications.cache_delete_pattern"), \
             patch("app.api.endpoints.medications.notify_family_medication_change"):
            response = await client.patch(
                f"/api/v1/medications/{medication_id}",
                json={
                    "name": "New Name",
                    "dosage": "10mg",
                },
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == medication_id

    @pytest.mark.asyncio
    async def test_update_medication_convert_to_prn(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should clear reminders/interval when converting to PRN."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id, name="Buddy")
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
            is_as_needed=False,
            reminders_enabled=True,
            interval_days=1,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic mocks
        pet_result2 = MagicMock()
        pet_result2.scalar_one.return_value = mock_pet

        # For deleting existing schedules
        existing_schedules_result = MagicMock()
        existing_schedules_result.scalars.return_value.all.return_value = []

        # For re-fetching medication with photos
        med_with_photos_result = MagicMock()
        med_with_photos_result.scalar_one.return_value = mock_medication

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                pet_result2,
                existing_schedules_result,
                med_with_photos_result,
            ]
        )
        mock_db_session.delete = AsyncMock()

        with patch("app.api.endpoints.medications.cache_delete_pattern"), \
             patch("app.api.endpoints.medications.notify_family_medication_change"):
            response = await client.patch(
                f"/api/v1/medications/{medication_id}",
                json={"is_as_needed": True},
                headers=auth_headers,
            )

        assert response.status_code == 200
        # Verify medication was updated to PRN
        assert mock_medication.is_as_needed == True

    @pytest.mark.asyncio
    async def test_update_medication_scheduled_times(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update scheduled reminder times."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id, name="Buddy")
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
            is_as_needed=False,
            reminders_enabled=True,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic mocks
        pet_result2 = MagicMock()
        pet_result2.scalar_one.return_value = mock_pet

        # For deleting existing schedules
        existing_schedules_result = MagicMock()
        existing_schedules_result.scalars.return_value.all.return_value = []

        # For re-fetching medication with photos
        med_with_photos_result = MagicMock()
        med_with_photos_result.scalar_one.return_value = mock_medication

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                pet_result2,
                existing_schedules_result,
                med_with_photos_result,
            ]
        )
        mock_db_session.delete = AsyncMock()

        # Mock db.add to set id on schedule objects
        def mock_add(obj):
            if not hasattr(obj, 'id') or obj.id is None:
                obj.id = str(uuid4())

        mock_db_session.add = mock_add

        with patch("app.api.endpoints.medications.cache_delete_pattern"), \
             patch("app.api.endpoints.medications.notify_family_medication_change"):
            response = await client.patch(
                f"/api/v1/medications/{medication_id}",
                json={
                    "scheduled_times": [
                        {"hour": 8, "minute": 0},
                        {"hour": 20, "minute": 0},
                    ]
                },
                headers=auth_headers,
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_medication_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 when medication doesn't exist."""
        medication_id = str(uuid4())

        # Mock RLS
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Mock pet not found
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, pet_result]
        )

        response = await client.patch(
            f"/api/v1/medications/{medication_id}",
            json={"name": "Updated Name"},
            headers=auth_headers,
        )

        assert response.status_code == 404


# ============== Delete Medication Tests ==============

class TestDeleteMedication:
    """Tests for DELETE /api/v1/medications/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_medication_hard_delete_no_doses(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should hard delete medication when no doses exist."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id, name="Buddy")
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
            name="Test Med",
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic mocks
        pet_result2 = MagicMock()
        pet_result2.scalar_one.return_value = mock_pet

        # Dose count query returns 0
        dose_count_result = MagicMock()
        dose_count_result.scalar.return_value = 0

        # Photos query returns empty
        photos_result = MagicMock()
        photos_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                pet_result2,
                dose_count_result,
                photos_result,
            ]
        )
        mock_db_session.delete = AsyncMock()

        with patch("app.api.endpoints.medications.cache_delete_pattern"), \
             patch("app.api.endpoints.medications.notify_family_medication_change"):
            response = await client.delete(
                f"/api/v1/medications/{medication_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == True
        assert data["archived"] == False

    @pytest.mark.asyncio
    async def test_delete_medication_archive_with_doses(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should archive medication when doses exist to preserve history."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id, name="Buddy")
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
            name="Test Med",
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic mocks
        pet_result2 = MagicMock()
        pet_result2.scalar_one.return_value = mock_pet

        # Dose count query returns 5
        dose_count_result = MagicMock()
        dose_count_result.scalar.return_value = 5

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                pet_result2,
                dose_count_result,
            ]
        )

        with patch("app.api.endpoints.medications.cache_delete_pattern"), \
             patch("app.api.endpoints.medications.notify_family_medication_change"):
            response = await client.delete(
                f"/api/v1/medications/{medication_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == False
        assert data["archived"] == True
        assert "5 dose record(s)" in data["message"]

    @pytest.mark.asyncio
    async def test_delete_medication_with_photos(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete photos from R2 on hard delete."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        photo_url = "https://example.com/photo.jpg"

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id, name="Buddy")
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        mock_photo = create_mock_photo(
            medication_id=medication_id, photo_url=photo_url
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic mocks
        pet_result2 = MagicMock()
        pet_result2.scalar_one.return_value = mock_pet

        # Dose count = 0
        dose_count_result = MagicMock()
        dose_count_result.scalar.return_value = 0

        # Photos query returns one photo
        photos_result = MagicMock()
        photos_result.scalars.return_value.all.return_value = [mock_photo]

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                pet_result2,
                dose_count_result,
                photos_result,
            ]
        )
        mock_db_session.delete = AsyncMock()

        mock_storage = AsyncMock()
        mock_storage.delete_image = AsyncMock(return_value=True)

        with patch("app.api.endpoints.medications.cache_delete_pattern"), \
             patch("app.api.endpoints.medications.notify_family_medication_change"), \
             patch("app.api.endpoints.medications.storage_service", mock_storage):
            response = await client.delete(
                f"/api/v1/medications/{medication_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        # Verify storage service was called
        mock_storage.delete_image.assert_called_once_with(photo_url)


# ============== Photo Upload/Delete Tests ==============

class TestMedicationPhotos:
    """Tests for medication photo upload/delete endpoints."""

    @pytest.mark.asyncio
    async def test_upload_photo_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully upload a photo."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        photo_url = "https://example.com/new-photo.jpg"

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic mocks
        # Photo count = 0
        photo_count_result = MagicMock()
        photo_count_result.scalar.return_value = 0

        # Pet query for org_id
        pet_result2 = MagicMock()
        pet_result2.scalar_one.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                photo_count_result,
                pet_result2,
            ]
        )

        # Mock db.add to set id and created_at on the photo object
        def mock_add(obj):
            obj.id = str(uuid4())
            obj.created_at = datetime(2024, 1, 1)

        mock_db_session.add = mock_add

        mock_storage = AsyncMock()
        mock_storage.upload_image = AsyncMock(return_value=photo_url)

        # Create a mock file
        from io import BytesIO
        file_content = BytesIO(b"fake image data")

        with patch("app.api.endpoints.medications.cache_delete_pattern"), \
             patch("app.api.endpoints.medications.storage_service", mock_storage):
            response = await client.post(
                f"/api/v1/medications/{medication_id}/photos",
                headers=auth_headers,
                files={"file": ("test.jpg", file_content, "image/jpeg")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["medication_id"] == medication_id
        assert data["photo_url"] == photo_url

    @pytest.mark.asyncio
    async def test_upload_photo_exceeds_limit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when photo limit (3) is reached."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Photo count = 3 (max limit)
        photo_count_result = MagicMock()
        photo_count_result.scalar.return_value = 3

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                photo_count_result,
            ]
        )

        from io import BytesIO
        file_content = BytesIO(b"fake image data")

        response = await client.post(
            f"/api/v1/medications/{medication_id}/photos",
            headers=auth_headers,
            files={"file": ("test.jpg", file_content, "image/jpeg")},
        )

        assert response.status_code == 400
        assert "Maximum 3 photos" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_photo_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully delete a photo."""
        medication_id = str(uuid4())
        photo_id = str(uuid4())
        pet_id = str(uuid4())
        photo_url = "https://example.com/photo.jpg"

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        mock_photo = create_mock_photo(
            photo_id=photo_id,
            medication_id=medication_id,
            photo_url=photo_url,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic mocks
        # Photo query
        photo_result = MagicMock()
        photo_result.scalar_one_or_none.return_value = mock_photo

        # Pet query for cache invalidation
        pet_result2 = MagicMock()
        pet_result2.scalar_one.return_value = mock_pet

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                photo_result,
                pet_result2,
            ]
        )
        mock_db_session.delete = AsyncMock()

        mock_storage = AsyncMock()
        mock_storage.delete_image = AsyncMock(return_value=True)

        with patch("app.api.endpoints.medications.cache_delete_pattern"), \
             patch("app.api.endpoints.medications.storage_service", mock_storage):
            response = await client.delete(
                f"/api/v1/medications/{medication_id}/photos/{photo_id}",
                headers=auth_headers,
            )

        assert response.status_code == 204
        mock_storage.delete_image.assert_called_once_with(photo_url)

    @pytest.mark.asyncio
    async def test_delete_photo_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 when photo doesn't exist."""
        medication_id = str(uuid4())
        photo_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Photo not found
        photo_result = MagicMock()
        photo_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                photo_result,
            ]
        )

        response = await client.delete(
            f"/api/v1/medications/{medication_id}/photos/{photo_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Photo not found" in response.json()["detail"]


# ============== Dose Management Tests ==============

class TestDoseManagement:
    """Tests for dose recording and management endpoints."""

    @pytest.mark.asyncio
    async def test_record_dose_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully record a dose."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic: medication + pet query for notification
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Business logic: user query for notification name
        mock_user = MagicMock()
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        # Business logic: get pet_id for cache invalidation
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = pet_id

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                med_pet_result,
                user_result,
                pet_id_result,
            ]
        )

        # Mock db.add to set id and created_at on the dose object
        def mock_add(obj):
            obj.id = str(uuid4())
            obj.created_at = datetime(2024, 1, 1)

        mock_db_session.add = mock_add

        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.notify_family_dose_administered", new_callable=AsyncMock):
            response = await client.post(
                "/api/v1/doses",
                json={
                    "medication_id": medication_id,
                    "notes": "Given with food",
                },
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["medication_id"] == medication_id
        assert data["given_by"] == test_user_id

    @pytest.mark.asyncio
    async def test_record_dose_custom_timestamp(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should record dose with custom given_at timestamp."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        custom_time = "2024-01-01T10:30:00Z"

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic: medication + pet query for notification
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Business logic: user query for notification name
        mock_user = MagicMock()
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = pet_id

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                med_pet_result,
                user_result,
                pet_id_result,
            ]
        )

        # Mock db.add to set id and created_at
        def mock_add(obj):
            obj.id = str(uuid4())
            obj.created_at = datetime(2024, 1, 1)

        mock_db_session.add = mock_add

        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.notify_family_dose_administered", new_callable=AsyncMock):
            response = await client.post(
                "/api/v1/doses",
                json={
                    "medication_id": medication_id,
                    "given_at": custom_time,
                },
                headers=auth_headers,
            )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_list_doses_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list doses with user names formatted."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        dose_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        mock_dose = create_mock_dose(
            dose_id=dose_id,
            medication_id=medication_id,
            given_by=test_user_id,
        )
        mock_user = create_mock_user(user_id=test_user_id)

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Business logic
        # Count query for pagination
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        # Doses query
        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = [mock_dose]

        # Users query
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                count_result,
                doses_result,
                users_result,
            ]
        )

        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["doses"]) == 1
        assert data["total"] == 1
        # Current user should show as "You"
        assert data["doses"][0]["given_by"] == "You"

    @pytest.mark.asyncio
    async def test_list_doses_with_limit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should respect limit parameter for pagination."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )

        # Mock authorization flow
        auth_mocks = setup_medication_access_mocks(
            mock_medication, mock_pet, mock_membership
        )

        # Count query for pagination
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        # Empty doses result
        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                count_result,
                doses_result,
            ]
        )

        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}?limit=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_update_dose_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully update a dose."""
        dose_id = str(uuid4())
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        mock_dose = create_mock_dose(
            dose_id=dose_id,
            medication_id=medication_id,
            given_by=test_user_id,
        )
        mock_user = create_mock_user(user_id=test_user_id)

        # Mock authorization flow (verify_dose_access)
        auth_mocks = setup_dose_access_mocks(
            mock_dose, mock_medication, mock_pet, mock_membership
        )

        # Business logic
        # For get pet_id from medication (cache invalidation)
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = pet_id

        # Users query for name formatting
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                pet_id_result,
                users_result,
            ]
        )

        with patch("app.api.endpoints.doses.cache_delete_pattern"):
            response = await client.patch(
                f"/api/v1/doses/{dose_id}",
                json={"notes": "Updated notes"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == dose_id

    @pytest.mark.asyncio
    async def test_delete_dose_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully delete a dose."""
        dose_id = str(uuid4())
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        mock_dose = create_mock_dose(
            dose_id=dose_id,
            medication_id=medication_id,
        )

        # Mock authorization flow (verify_dose_access)
        auth_mocks = setup_dose_access_mocks(
            mock_dose, mock_medication, mock_pet, mock_membership
        )

        # For get pet_id from medication (cache invalidation)
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = pet_id

        mock_db_session.execute = AsyncMock(
            side_effect=auth_mocks + [
                pet_id_result,
            ]
        )
        mock_db_session.delete = AsyncMock()

        with patch("app.api.endpoints.doses.cache_delete_pattern"):
            response = await client.delete(
                f"/api/v1/doses/{dose_id}",
                headers=auth_headers,
            )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_dose_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 when dose doesn't exist."""
        dose_id = str(uuid4())

        # Mock RLS
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        # Mock membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )

        # Mock pet not found
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result, membership_result, pet_result]
        )

        response = await client.delete(
            f"/api/v1/doses/{dose_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
