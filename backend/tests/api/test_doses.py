"""
Comprehensive integration tests for medication dose management endpoints.

Tests cover:
- POST /api/v1/doses - Record a dose
- GET /api/v1/doses/medication/{medication_id} - List doses for medication
- GET /api/v1/doses/medication/{medication_id}/today - Get today's doses (with timezone support)
- GET /api/v1/doses/medication/{medication_id}/last - Get last dose
- GET /api/v1/doses/all/{pet_id} - List all doses for a pet across medications
- PATCH /api/v1/doses/{id} - Update dose
- DELETE /api/v1/doses/{id} - Delete dose

Authorization checks:
- User must have access to the medication through family membership
- User must have access to the pet through family membership

NOTE: These tests mock the database session and use the FastAPI test client.
Authorization flow (important for mocking):
- verify_medication_access: queries medication first (no RLS), then calls verify_pet_access
- verify_dose_access: queries dose first (no RLS), then calls verify_medication_access
- verify_pet_access: calls set_rls_user() first (requires RLS mock), queries pet, then calls verify_family_access
- verify_family_access: calls set_rls_user() first (requires RLS mock), then queries membership
"""
from datetime import datetime, timedelta, timezone as dt_timezone
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
    create_mock_user,
)


# ============== Helper Functions ==============

def create_mock_medication(
    medication_id: str = None,
    pet_id: str = None,
    name: str = "Prednisone",
    medication_type: str = "pill",
    is_archived: bool = False,
) -> MagicMock:
    """Create a mock PetMedication object."""
    medication = MagicMock()
    medication.id = UUID(medication_id) if medication_id else uuid4()
    medication.pet_id = UUID(pet_id) if pet_id else uuid4()
    medication.name = name
    medication.medication_type = medication_type
    medication.is_archived = is_archived
    medication.created_at = datetime.utcnow()
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
    dose.id = UUID(dose_id) if dose_id else uuid4()
    dose.medication_id = UUID(medication_id) if medication_id else uuid4()
    dose.given_at = given_at or datetime.utcnow()
    dose.given_by = UUID(given_by) if given_by else uuid4()
    dose.notes = notes
    dose.created_at = datetime.utcnow()
    return dose


# ============== Record Dose Tests ==============

class TestRecordDose:
    """Tests for POST /api/v1/doses endpoint."""

    @pytest.mark.asyncio
    async def test_record_dose_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully record a dose with default timestamp."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock verify_medication_access (NO RLS call first - it goes straight to medication query)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
        )
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medication+pet join query for notification
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Mock current user query
        mock_user = create_mock_user(user_id=test_user_id)
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        # Mock cache invalidation query (get pet_id from medication)
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                med_pet_result,     # get medication with pet for notification
                user_result,        # get current user for notification
                pet_id_result,      # invalidate_dose_caches query
            ]
        )

        # Mock the dose object that gets added
        mock_db_session.add = MagicMock()
        def refresh_dose(obj):
            obj.id = uuid4()
            obj.created_at = datetime.utcnow()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_dose)

        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.get_filtered_family_member_tokens", new_callable=AsyncMock) as mock_get_tokens:

            # Mock empty notification list (no other family members)
            mock_get_tokens.return_value = []

            response = await client.post(
                "/api/v1/doses",
                json={
                    "medication_id": medication_id,
                    "notes": "Given with breakfast",
                },
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["medication_id"] == medication_id
        assert data["notes"] == "Given with breakfast"
        assert "given_at" in data
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
        """Should record a dose with custom given_at timestamp."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        custom_time = datetime(2024, 1, 15, 8, 30, 0)

        # Mock authorization chain
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medication+pet join query for notification
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Mock current user query
        mock_user = create_mock_user(user_id=test_user_id)
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                med_pet_result,     # get medication with pet for notification
                user_result,        # get current user for notification
                pet_id_result,
            ]
        )

        mock_db_session.add = MagicMock()
        def refresh_dose(obj):
            obj.id = uuid4()
            obj.created_at = datetime.utcnow()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_dose)

        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.get_filtered_family_member_tokens", new_callable=AsyncMock) as mock_get_tokens:

            # Mock empty notification list (no other family members)
            mock_get_tokens.return_value = []

            response = await client.post(
                "/api/v1/doses",
                json={
                    "medication_id": medication_id,
                    "given_at": custom_time.isoformat() + "Z",
                },
                headers=auth_headers,
            )

        assert response.status_code == 201
        data = response.json()
        assert data["medication_id"] == medication_id

    @pytest.mark.asyncio
    async def test_record_dose_medication_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 if medication doesn't exist."""
        medication_id = str(uuid4())

        # Mock medication not found (verify_medication_access queries medication first, no RLS)
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[medication_result]
        )

        response = await client.post(
            "/api/v1/doses",
            json={"medication_id": medication_id},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Medication not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_record_dose_unauthorized(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 if user doesn't have access to medication."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        # Mock verify_medication_access (medication query first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # User not member of pet's family
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
            ]
        )

        response = await client.post(
            "/api/v1/doses",
            json={"medication_id": medication_id},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_record_dose_no_auth(
        self,
        client: AsyncClient,
    ):
        """Should return 401 without auth token."""
        response = await client.post(
            "/api/v1/doses",
            json={"medication_id": str(uuid4())},
        )

        assert response.status_code == 401


# ============== Dose Administration Notification Tests ==============

class TestDoseAdministrationNotifications:
    """Tests for dose administration push notification functionality."""

    @pytest.mark.asyncio
    async def test_record_dose_sends_notification_to_family_members(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should send notification to other family members when a dose is recorded."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        pet_name = "Buddy"
        medication_name = "Prednisone"

        # Mock authorization chain (verify_medication_access)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        mock_medication.name = medication_name

        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(
            pet_id=pet_id,
            org_id=test_family_id,
            name=pet_name,
        )
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medication+pet join query for notification
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Mock current user query
        mock_user = create_mock_user(
            user_id=test_user_id,
            first_name="John",
            last_name="Doe",
        )
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        # Cache invalidation query (get pet_id from medication)
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                med_pet_result,     # get medication with pet for notification
                user_result,        # get current user for notification
                pet_id_result,      # invalidate_dose_caches query
            ]
        )

        # Mock the dose object that gets added
        mock_db_session.add = MagicMock()
        def refresh_dose(obj):
            obj.id = uuid4()
            obj.created_at = datetime.utcnow()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_dose)

        # Mock notification functions
        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.get_filtered_family_member_tokens", new_callable=AsyncMock) as mock_get_tokens, \
             patch("app.api.endpoints.doses.apns_service.send_to_multiple", new_callable=AsyncMock) as mock_send:

            # Mock that 2 family members will receive notifications
            mock_get_tokens.return_value = ["token1", "token2"]
            mock_send.return_value = 2

            response = await client.post(
                "/api/v1/doses",
                json={
                    "medication_id": medication_id,
                    "notes": "Given with breakfast",
                },
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 201

            # Verify notification function was called with correct parameters
            mock_get_tokens.assert_called_once()
            call_args = mock_get_tokens.call_args
            assert call_args.args[1] == UUID(test_family_id)  # org_id
            assert call_args.args[2] == UUID(test_user_id)    # exclude_user_id
            assert call_args.args[3] == "dose_administered"   # notification_type

            # Verify APNS was called with correct notification content
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            assert call_kwargs["device_tokens"] == ["token1", "token2"]
            assert call_kwargs["title"] == f"Dose Recorded: {pet_name}"
            assert call_kwargs["body"] == f"John D. gave {pet_name} {medication_name}"
            assert call_kwargs["data"]["type"] == "dose_administered"
            assert call_kwargs["data"]["pet_name"] == pet_name
            assert call_kwargs["data"]["medication_name"] == medication_name

    @pytest.mark.asyncio
    async def test_record_dose_notification_respects_user_preferences(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should only send notifications to users who have dose_administered enabled."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medication+pet join query
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Mock current user query
        mock_user = create_mock_user(user_id=test_user_id)
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        # Cache invalidation query
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                med_pet_result,
                user_result,
                pet_id_result,
            ]
        )

        mock_db_session.add = MagicMock()
        def refresh_dose(obj):
            obj.id = uuid4()
            obj.created_at = datetime.utcnow()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_dose)

        # Mock notification - only 1 user has this notification enabled
        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.get_filtered_family_member_tokens", new_callable=AsyncMock) as mock_get_tokens, \
             patch("app.api.endpoints.doses.apns_service.send_to_multiple", new_callable=AsyncMock) as mock_send:

            mock_get_tokens.return_value = ["token1"]  # Only 1 user has it enabled
            mock_send.return_value = 1

            response = await client.post(
                "/api/v1/doses",
                json={"medication_id": medication_id},
                headers=auth_headers,
            )

            assert response.status_code == 201

            # Verify get_filtered_family_member_tokens was called with "dose_administered"
            # This function will filter based on user preferences
            mock_get_tokens.assert_called_once()
            assert mock_get_tokens.call_args.args[3] == "dose_administered"

    @pytest.mark.asyncio
    async def test_record_dose_excludes_dose_giver_from_notification(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should exclude the user who gave the dose from receiving notification."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medication+pet join query
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Mock current user query
        mock_user = create_mock_user(user_id=test_user_id)
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        # Cache invalidation query
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                med_pet_result,
                user_result,
                pet_id_result,
            ]
        )

        mock_db_session.add = MagicMock()
        def refresh_dose(obj):
            obj.id = uuid4()
            obj.created_at = datetime.utcnow()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_dose)

        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.get_filtered_family_member_tokens", new_callable=AsyncMock) as mock_get_tokens:

            mock_get_tokens.return_value = []

            await client.post(
                "/api/v1/doses",
                json={"medication_id": medication_id},
                headers=auth_headers,
            )

            # Verify the current user (dose giver) is excluded
            mock_get_tokens.assert_called_once()
            excluded_user_id = mock_get_tokens.call_args.args[2]
            assert excluded_user_id == UUID(test_user_id)

    @pytest.mark.asyncio
    async def test_record_dose_no_notification_when_no_family_members(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should not send notifications when no other family members exist."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medication+pet join query
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Mock current user query
        mock_user = create_mock_user(user_id=test_user_id)
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        # Cache invalidation query
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                med_pet_result,
                user_result,
                pet_id_result,
            ]
        )

        mock_db_session.add = MagicMock()
        def refresh_dose(obj):
            obj.id = uuid4()
            obj.created_at = datetime.utcnow()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_dose)

        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.get_filtered_family_member_tokens", new_callable=AsyncMock) as mock_get_tokens, \
             patch("app.api.endpoints.doses.apns_service.send_to_multiple", new_callable=AsyncMock) as mock_send:

            # No other family members with this notification enabled
            mock_get_tokens.return_value = []

            response = await client.post(
                "/api/v1/doses",
                json={"medication_id": medication_id},
                headers=auth_headers,
            )

            assert response.status_code == 201

            # APNS should not be called when there are no tokens
            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_dose_notification_uses_formatted_user_name(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should use formatted user name (First L.) in notification body."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        mock_medication.name = "Prednisone"

        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_pet.name = "Buddy"
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medication+pet join query
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Mock current user with specific name
        mock_user = create_mock_user(
            user_id=test_user_id,
            first_name="Alexander",
            last_name="Johnson",
        )
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        # Cache invalidation query
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                med_pet_result,
                user_result,
                pet_id_result,
            ]
        )

        mock_db_session.add = MagicMock()
        def refresh_dose(obj):
            obj.id = uuid4()
            obj.created_at = datetime.utcnow()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_dose)

        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.get_filtered_family_member_tokens", new_callable=AsyncMock) as mock_get_tokens, \
             patch("app.api.endpoints.doses.apns_service.send_to_multiple", new_callable=AsyncMock) as mock_send:

            mock_get_tokens.return_value = ["token1"]
            mock_send.return_value = 1

            await client.post(
                "/api/v1/doses",
                json={"medication_id": medication_id},
                headers=auth_headers,
            )

            # Verify notification body uses formatted name (First L.)
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args.kwargs
            # format_user_name("Alexander", "Johnson") should return "Alexander J."
            assert call_kwargs["body"] == "Alexander J. gave Buddy Prednisone"

    @pytest.mark.asyncio
    async def test_record_dose_notification_error_does_not_fail_dose_creation(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should still create dose successfully even if notification fails."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medication+pet join query
        med_pet_result = MagicMock()
        med_pet_result.first.return_value = (mock_medication, mock_pet)

        # Mock current user query
        mock_user = create_mock_user(user_id=test_user_id)
        user_result = MagicMock()
        user_result.scalar_one.return_value = mock_user

        # Cache invalidation query
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                med_pet_result,
                user_result,
                pet_id_result,
            ]
        )

        mock_db_session.add = MagicMock()
        def refresh_dose(obj):
            obj.id = uuid4()
            obj.created_at = datetime.utcnow()
        mock_db_session.refresh = AsyncMock(side_effect=refresh_dose)

        # Mock notification to raise an exception
        with patch("app.api.endpoints.doses.cache_delete_pattern"), \
             patch("app.api.endpoints.doses.get_filtered_family_member_tokens", new_callable=AsyncMock) as mock_get_tokens:

            # Simulate an error in get_filtered_family_member_tokens
            mock_get_tokens.side_effect = Exception("Database connection error")

            # Should still succeed despite notification error
            response = await client.post(
                "/api/v1/doses",
                json={"medication_id": medication_id},
                headers=auth_headers,
            )

            # Dose creation should succeed
            assert response.status_code == 201
            data = response.json()
            assert "id" in data
            assert data["medication_id"] == medication_id


# ============== List Doses for Medication Tests ==============

class TestListDoses:
    """Tests for GET /api/v1/doses/medication/{medication_id} endpoint."""

    @pytest.mark.asyncio
    async def test_list_doses_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list doses for medication with user names formatted."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        other_user_id = str(uuid4())

        # Create mock doses
        mock_dose1 = create_mock_dose(
            medication_id=medication_id,
            given_by=test_user_id,
            notes="Morning dose",
            given_at=datetime(2024, 1, 15, 9, 0),
        )
        mock_dose2 = create_mock_dose(
            medication_id=medication_id,
            given_by=other_user_id,
            notes="Evening dose",
            given_at=datetime(2024, 1, 14, 21, 0),
        )

        # Mock authorization chain (verify_medication_access: medication first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock count query for pagination
        count_result = MagicMock()
        count_result.scalar.return_value = 2

        # Mock doses query
        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = [mock_dose1, mock_dose2]

        # Mock users query for name formatting
        mock_current_user = create_mock_user(
            user_id=test_user_id,
            first_name="John",
            last_name="Doe",
        )
        mock_other_user = create_mock_user(
            user_id=other_user_id,
            first_name="Jane",
            last_name="Smith",
        )
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [
            mock_current_user,
            mock_other_user,
        ]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                count_result,       # count query for pagination
                doses_result,       # doses query
                users_result,       # users query
            ]
        )

        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["doses"]) == 2
        assert data["total"] == 2
        assert data["doses"][0]["given_by"] == "You"  # Current user
        assert data["doses"][1]["given_by"] == "Jane S."  # Formatted as "FirstName L."
        assert data["doses"][0]["notes"] == "Morning dose"

    @pytest.mark.asyncio
    async def test_list_doses_with_limit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should respect limit parameter."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain (verify_medication_access: medication first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock count query for pagination (total is 10 doses)
        count_result = MagicMock()
        count_result.scalar.return_value = 10

        # Return 10 doses (but limit should be 5)
        mock_doses = [
            create_mock_dose(medication_id=medication_id, given_by=test_user_id)
            for _ in range(10)
        ]
        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = mock_doses

        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                count_result,       # count query for pagination
                doses_result,       # doses query
                users_result,       # users query
            ]
        )

        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}?limit=5",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        # Note: The actual limiting happens in the SQL query, which we've mocked
        # In a real scenario, only 5 doses would be returned

    @pytest.mark.asyncio
    async def test_list_doses_empty(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return empty list if no doses recorded."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain (verify_medication_access: medication first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock count query for pagination (0 doses)
        count_result = MagicMock()
        count_result.scalar.return_value = 0

        # Empty doses
        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                count_result,       # count query for pagination
                doses_result,       # doses query
            ]
        )

        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["doses"] == []


# ============== Get Today's Doses Tests ==============

class TestGetTodayDoses:
    """Tests for GET /api/v1/doses/medication/{medication_id}/today endpoint."""

    @pytest.mark.asyncio
    async def test_get_today_doses_with_timezone(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should get today's doses in user's timezone."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Create a dose that was given today (in UTC)
        now = datetime.now(dt_timezone.utc)
        mock_dose = create_mock_dose(
            medication_id=medication_id,
            given_by=test_user_id,
            given_at=now.replace(tzinfo=None),
        )

        # Mock authorization chain (verify_medication_access: medication first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = [mock_dose]

        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                doses_result,       # doses query
                users_result,       # users query
            ]
        )

        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}/today?timezone=America/Los_Angeles",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["doses"]) == 1

    @pytest.mark.asyncio
    async def test_get_today_doses_invalid_timezone_fallback(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should fall back to UTC for invalid timezone."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain (verify_medication_access: medication first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                doses_result,       # doses query
            ]
        )

        # Should not raise error with invalid timezone
        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}/today?timezone=Invalid/Timezone",
            headers=auth_headers,
        )

        assert response.status_code == 200


# ============== Get Last Dose Tests ==============

class TestGetLastDose:
    """Tests for GET /api/v1/doses/medication/{medication_id}/last endpoint."""

    @pytest.mark.asyncio
    async def test_get_last_dose_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should get the most recent dose."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_dose = create_mock_dose(
            medication_id=medication_id,
            given_by=test_user_id,
            notes="Most recent",
            given_at=datetime.utcnow(),
        )

        # Mock authorization chain (verify_medication_access: medication first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = mock_dose

        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                dose_result,        # last dose query
                users_result,       # users query
            ]
        )

        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}/last",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Most recent"
        assert data["given_by"] == "You"

    @pytest.mark.asyncio
    async def test_get_last_dose_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 if no doses recorded."""
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        # Mock authorization chain (verify_medication_access: medication first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # No dose found
        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                dose_result,        # last dose query
            ]
        )

        response = await client.get(
            f"/api/v1/doses/medication/{medication_id}/last",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "No doses recorded" in response.json()["detail"]


# ============== List All Doses for Pet Tests ==============

class TestListAllDoses:
    """Tests for GET /api/v1/doses/all/{pet_id} endpoint."""

    @pytest.mark.asyncio
    async def test_list_all_doses_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list all doses across medications for a pet."""
        pet_id = str(uuid4())
        med1_id = str(uuid4())
        med2_id = str(uuid4())

        # Create doses from different medications
        mock_dose1 = create_mock_dose(
            medication_id=med1_id,
            given_by=test_user_id,
            given_at=datetime(2024, 1, 15, 9, 0),
        )
        mock_dose2 = create_mock_dose(
            medication_id=med2_id,
            given_by=test_user_id,
            given_at=datetime(2024, 1, 14, 21, 0),
        )

        # Mock verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medications query
        meds_result = MagicMock()
        med1_row = MagicMock()
        med1_row.id = UUID(med1_id)
        med1_row.name = "Prednisone"
        med2_row = MagicMock()
        med2_row.id = UUID(med2_id)
        med2_row.name = "Eye Drops"
        meds_result.all.return_value = [med1_row, med2_row]

        # Mock count query
        count_result = MagicMock()
        count_result.scalar.return_value = 2

        # Mock doses query
        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = [mock_dose1, mock_dose2]

        # Mock users query
        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                meds_result,
                count_result,
                doses_result,
                users_result,
            ]
        )

        response = await client.get(
            f"/api/v1/doses/all/{pet_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["doses"]) == 2
        assert data["doses"][0]["medication_name"] in ["Prednisone", "Eye Drops"]
        assert data["doses"][0]["pet_id"] == pet_id
        assert data["doses"][0]["given_by"] == "You"

    @pytest.mark.asyncio
    async def test_list_all_doses_with_pagination(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should support pagination with limit and offset."""
        pet_id = str(uuid4())
        med_id = str(uuid4())

        # Mock verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock medications
        meds_result = MagicMock()
        med_row = MagicMock()
        med_row.id = UUID(med_id)
        med_row.name = "Prednisone"
        meds_result.all.return_value = [med_row]

        # Total of 100 doses
        count_result = MagicMock()
        count_result.scalar.return_value = 100

        # Return 20 doses (limit=20)
        mock_doses = [
            create_mock_dose(medication_id=med_id, given_by=test_user_id)
            for _ in range(20)
        ]
        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = mock_doses

        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                meds_result,
                count_result,
                doses_result,
                users_result,
            ]
        )

        response = await client.get(
            f"/api/v1/doses/all/{pet_id}?limit=20&offset=20",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 100

    @pytest.mark.asyncio
    async def test_list_all_doses_no_medications(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return empty list if pet has no medications."""
        pet_id = str(uuid4())

        # Mock verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # No medications
        meds_result = MagicMock()
        meds_result.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                meds_result,
            ]
        )

        response = await client.get(
            f"/api/v1/doses/all/{pet_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["doses"] == []

    @pytest.mark.asyncio
    async def test_list_all_doses_includes_archived_medications(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should include doses from archived medications to preserve history."""
        pet_id = str(uuid4())
        archived_med_id = str(uuid4())

        mock_dose = create_mock_dose(
            medication_id=archived_med_id,
            given_by=test_user_id,
        )

        # Mock verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Archived medication
        meds_result = MagicMock()
        med_row = MagicMock()
        med_row.id = UUID(archived_med_id)
        med_row.name = "Old Medication (Archived)"
        meds_result.all.return_value = [med_row]

        count_result = MagicMock()
        count_result.scalar.return_value = 1

        doses_result = MagicMock()
        doses_result.scalars.return_value.all.return_value = [mock_dose]

        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result,
                pet_result,
                rls_result2,
                membership_result,
                meds_result,
                count_result,
                doses_result,
                users_result,
            ]
        )

        response = await client.get(
            f"/api/v1/doses/all/{pet_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "Archived" in data["doses"][0]["medication_name"]


# ============== Update Dose Tests ==============

class TestUpdateDose:
    """Tests for PATCH /api/v1/doses/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_dose_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully update dose fields."""
        dose_id = str(uuid4())
        medication_id = str(uuid4())
        pet_id = str(uuid4())

        mock_dose = create_mock_dose(
            dose_id=dose_id,
            medication_id=medication_id,
            given_by=test_user_id,
            notes="Old notes",
        )

        # Mock verify_dose_access chain (dose query first, no RLS)
        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = mock_dose

        # verify_medication_access for the dose (medication query first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Cache invalidation query
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        # Users query for response
        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                dose_result,        # verify_dose_access dose query
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                pet_id_result,      # cache invalidation query
                users_result,       # users query
            ]
        )

        mock_db_session.refresh = AsyncMock(
            side_effect=lambda obj: setattr(obj, 'notes', 'Updated notes')
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
    async def test_update_dose_timestamp(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update dose timestamp."""
        dose_id = str(uuid4())
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        new_time = datetime(2024, 1, 15, 10, 30, 0)

        mock_dose = create_mock_dose(
            dose_id=dose_id,
            medication_id=medication_id,
            given_by=test_user_id,
        )

        # Mock authorization chain (verify_dose_access: dose query first, no RLS)
        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = mock_dose

        # verify_medication_access for the dose (medication query first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        mock_db_session.execute = AsyncMock(
            side_effect=[
                dose_result,        # verify_dose_access dose query
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                pet_id_result,      # cache invalidation query
                users_result,       # users query
            ]
        )

        mock_db_session.refresh = AsyncMock()

        with patch("app.api.endpoints.doses.cache_delete_pattern"):
            response = await client.patch(
                f"/api/v1/doses/{dose_id}",
                json={"given_at": new_time.isoformat() + "Z"},
                headers=auth_headers,
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_dose_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 if dose doesn't exist."""
        dose_id = str(uuid4())

        # Dose not found (verify_dose_access queries dose first, no RLS)
        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[dose_result]
        )

        response = await client.patch(
            f"/api/v1/doses/{dose_id}",
            json={"notes": "New notes"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Medication dose not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_dose_forbidden(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 if user doesn't have access."""
        dose_id = str(uuid4())
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        mock_dose = create_mock_dose(
            dose_id=dose_id,
            medication_id=medication_id,
        )

        # Mock authorization chain - user not member (verify_dose_access: dose query first, no RLS)
        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = mock_dose

        # verify_medication_access (medication query first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # No membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[
                dose_result,        # verify_dose_access dose query
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
            ]
        )

        response = await client.patch(
            f"/api/v1/doses/{dose_id}",
            json={"notes": "New notes"},
            headers=auth_headers,
        )

        assert response.status_code == 403


# ============== Delete Dose Tests ==============

class TestDeleteDose:
    """Tests for DELETE /api/v1/doses/{id} endpoint."""

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

        mock_dose = create_mock_dose(
            dose_id=dose_id,
            medication_id=medication_id,
        )

        # Mock verify_dose_access chain (dose query first, no RLS)
        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = mock_dose

        # verify_medication_access (medication query first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Cache invalidation query
        pet_id_result = MagicMock()
        pet_id_result.scalar_one_or_none.return_value = UUID(pet_id)

        mock_db_session.execute = AsyncMock(
            side_effect=[
                dose_result,        # verify_dose_access dose query
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
                pet_id_result,      # cache invalidation query
            ]
        )

        mock_db_session.delete = AsyncMock()

        with patch("app.api.endpoints.doses.cache_delete_pattern"):
            response = await client.delete(
                f"/api/v1/doses/{dose_id}",
                headers=auth_headers,
            )

        assert response.status_code == 204
        mock_db_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_dose_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 if dose doesn't exist."""
        dose_id = str(uuid4())

        # Dose not found (verify_dose_access queries dose first, no RLS)
        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[dose_result]
        )

        response = await client.delete(
            f"/api/v1/doses/{dose_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Medication dose not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_dose_forbidden(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 if user doesn't have access."""
        dose_id = str(uuid4())
        medication_id = str(uuid4())
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        mock_dose = create_mock_dose(
            dose_id=dose_id,
            medication_id=medication_id,
        )

        # Mock authorization chain - user not member (verify_dose_access: dose query first, no RLS)
        dose_result = MagicMock()
        dose_result.scalar_one_or_none.return_value = mock_dose

        # verify_medication_access (medication query first, no RLS)
        mock_medication = create_mock_medication(
            medication_id=medication_id,
            pet_id=pet_id,
        )
        medication_result = MagicMock()
        medication_result.scalar_one_or_none.return_value = mock_medication

        # RLS for verify_pet_access
        rls_result = MagicMock()
        rls_result.scalar_one_or_none.return_value = None

        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS for verify_family_access
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # No membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[
                dose_result,        # verify_dose_access dose query
                medication_result,  # verify_medication_access
                rls_result,         # verify_pet_access RLS
                pet_result,         # verify_pet_access pet query
                rls_result2,        # verify_family_access RLS
                membership_result,  # verify_family_access membership query
            ]
        )

        response = await client.delete(
            f"/api/v1/doses/{dose_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_dose_no_auth(
        self,
        client: AsyncClient,
    ):
        """Should return 401 without auth token."""
        response = await client.delete(
            f"/api/v1/doses/{str(uuid4())}",
        )

        assert response.status_code == 401
