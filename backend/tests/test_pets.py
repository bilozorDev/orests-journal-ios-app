"""
Tests for pet management endpoints.
"""
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
    create_mock_pet,
)


class TestCreatePet:
    """Tests for POST /pets endpoint."""

    @pytest.mark.asyncio
    async def test_create_pet_with_date_of_birth(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create pet with date_of_birth."""
        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_pet = create_mock_pet(
            family_id=test_family_id,
            name="Buddy",
            kind="dog",
            date_of_birth=date(2022, 3, 15),
            created_by=test_user_id,
        )

        # Mock database queries
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        # Mock the refresh to set pet attributes
        async def mock_refresh(obj):
            obj.id = mock_pet.id
            obj.created_at = mock_pet.created_at

        mock_db_session.refresh = mock_refresh

        # Make request
        response = await client.post(
            f"/api/v1/pets?family_id={test_family_id}",
            json={
                "name": "Buddy",
                "kind": "dog",
                "date_of_birth": "2022-03-15",
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Buddy"
        assert data["kind"] == "dog"
        assert data["date_of_birth"] == "2022-03-15"

    @pytest.mark.asyncio
    async def test_create_pet_without_date_of_birth(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create pet without date_of_birth (null)."""
        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_pet = create_mock_pet(
            family_id=test_family_id,
            name="Luna",
            kind="cat",
            date_of_birth=None,
            created_by=test_user_id,
        )

        # Mock database queries
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        # Mock the refresh to set pet attributes
        async def mock_refresh(obj):
            obj.id = mock_pet.id
            obj.created_at = mock_pet.created_at
            obj.date_of_birth = None

        mock_db_session.refresh = mock_refresh

        # Make request
        response = await client.post(
            f"/api/v1/pets?family_id={test_family_id}",
            json={
                "name": "Luna",
                "kind": "cat",
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Luna"
        assert data["date_of_birth"] is None


class TestUpdatePet:
    """Tests for PATCH /pets/{pet_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_pet_date_of_birth(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update pet's date_of_birth."""
        pet_id = str(uuid4())

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_pet = create_mock_pet(
            pet_id=pet_id,
            family_id=test_family_id,
            name="Max",
            kind="dog",
            date_of_birth=None,
        )

        # Mock database queries
        # The endpoint flow is:
        # 1. set_rls_user (RLS setup) - no result needed
        # 2. Query for Pet
        # 3. set_rls_user (RLS setup in verify_family_access) - no result needed
        # 4. Query for FamilyMember (in verify_family_access)
        # 5. Query for FamilyMembers (in get_filtered_family_member_tokens)
        # 6. Query for NotificationPreferences
        # 7. Query for DeviceTokens
        rls_result1 = MagicMock()
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet
        rls_result2 = MagicMock()
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Notification-related queries (return empty lists)
        family_members_result = MagicMock()
        family_members_result.scalars.return_value.all.return_value = []
        prefs_result = MagicMock()
        prefs_result.scalars.return_value.all.return_value = []
        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result1,
                pet_result,
                rls_result2,
                membership_result,
                family_members_result,
                prefs_result,
                tokens_result,
            ]
        )

        # Make request to update date_of_birth
        response = await client.patch(
            f"/api/v1/pets/{pet_id}",
            json={"date_of_birth": "2020-06-01"},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        # Verify that date_of_birth was updated on the mock
        assert mock_pet.date_of_birth == date(2020, 6, 1)

    @pytest.mark.asyncio
    async def test_clear_pet_date_of_birth(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should clear date_of_birth by setting to null."""
        pet_id = str(uuid4())

        # Setup mocks - pet has existing date_of_birth
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_pet = create_mock_pet(
            pet_id=pet_id,
            family_id=test_family_id,
            name="Rocky",
            kind="hamster",
            date_of_birth=date(2021, 1, 1),
        )

        # Mock database queries
        # The endpoint flow is:
        # 1. set_rls_user (RLS setup) - no result needed
        # 2. Query for Pet
        # 3. set_rls_user (RLS setup in verify_family_access) - no result needed
        # 4. Query for FamilyMember (in verify_family_access)
        # 5. Query for FamilyMembers (in get_filtered_family_member_tokens)
        # 6. Query for NotificationPreferences
        # 7. Query for DeviceTokens
        rls_result1 = MagicMock()
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet
        rls_result2 = MagicMock()
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Notification-related queries (return empty lists)
        family_members_result = MagicMock()
        family_members_result.scalars.return_value.all.return_value = []
        prefs_result = MagicMock()
        prefs_result.scalars.return_value.all.return_value = []
        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                rls_result1,
                pet_result,
                rls_result2,
                membership_result,
                family_members_result,
                prefs_result,
                tokens_result,
            ]
        )

        # Make request to clear date_of_birth
        response = await client.patch(
            f"/api/v1/pets/{pet_id}",
            json={"date_of_birth": None},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        # Verify that date_of_birth was cleared
        assert mock_pet.date_of_birth is None


class TestGetPet:
    """Tests for GET /pets/{pet_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_pet_includes_date_of_birth(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should include date_of_birth in response."""
        pet_id = str(uuid4())
        dob = date(2019, 8, 15)

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_pet = create_mock_pet(
            pet_id=pet_id,
            family_id=test_family_id,
            name="Whiskers",
            kind="cat",
            date_of_birth=dob,
        )

        # Mock database queries
        # The endpoint flow is:
        # 1. set_rls_user (RLS setup) - no result needed
        # 2. Query for Pet
        # 3. set_rls_user (RLS setup in verify_family_access) - no result needed
        # 4. Query for FamilyMember
        rls_result1 = MagicMock()
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet
        rls_result2 = MagicMock()
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, pet_result, rls_result2, membership_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/pets/{pet_id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Whiskers"
        assert data["date_of_birth"] == "2019-08-15"

    @pytest.mark.asyncio
    async def test_get_pet_with_null_date_of_birth(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return null for date_of_birth when not set."""
        pet_id = str(uuid4())

        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_pet = create_mock_pet(
            pet_id=pet_id,
            family_id=test_family_id,
            name="Buddy",
            kind="dog",
            date_of_birth=None,
        )

        # Mock database queries
        # The endpoint flow is:
        # 1. set_rls_user (RLS setup) - no result needed
        # 2. Query for Pet
        # 3. set_rls_user (RLS setup in verify_family_access) - no result needed
        # 4. Query for FamilyMember
        rls_result1 = MagicMock()
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet
        rls_result2 = MagicMock()
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[rls_result1, pet_result, rls_result2, membership_result]
        )

        # Make request
        response = await client.get(
            f"/api/v1/pets/{pet_id}",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Buddy"
        assert data["date_of_birth"] is None
