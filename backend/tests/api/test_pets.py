"""Tests for pets API endpoints.

Tests cover:
- Authorization checks (no auth, wrong family)
- Basic validation errors
- Successful CRUD operations
- Photo URL validation
- Health records
- Cache invalidation
"""
import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

from httpx import AsyncClient
from fastapi import status

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_pet,
    create_mock_membership,
)


# Test data
TEST_PET_ID = uuid4()
TEST_OTHER_FAMILY_ID = uuid4()


def setup_family_access_verification(
    mock_db_session: AsyncMock,
    mock_membership,
    additional_results=None,
):
    """
    Helper to set up db.execute mock for verify_family_access.

    verify_family_access:
    1. Executes RLS SET LOCAL query
    2. Queries for membership
    """
    results = []

    # RLS SET LOCAL
    rls_result = MagicMock()
    rls_result.scalar_one_or_none.return_value = None
    results.append(rls_result)

    # Membership query
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = mock_membership
    results.append(membership_result)

    # Add any additional results
    if additional_results:
        results.extend(additional_results)

    mock_db_session.execute = AsyncMock(side_effect=results)


def setup_pet_access_verification(
    mock_db_session: AsyncMock,
    mock_pet,
    mock_membership,
    additional_results=None,
):
    """
    Helper for endpoints that use verify_pet_access.

    verify_pet_access:
    1. Executes RLS SET LOCAL query
    2. Queries for pet
    3. Executes RLS SET LOCAL query (from verify_family_access)
    4. Queries for membership
    """
    results = []

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


class TestPetAuthorization:
    """Tests for authorization on pet endpoints."""

    @pytest.mark.asyncio
    async def test_list_pets_requires_auth(self, client: AsyncClient):
        """Should return 401 when no auth token provided."""
        response = await client.get(f"/api/v1/pets?family_id={TEST_FAMILY_ID}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_create_pet_requires_auth(self, client: AsyncClient):
        """Should return 401 when no auth token provided."""
        response = await client.post(
            f"/api/v1/pets?family_id={TEST_FAMILY_ID}",
            json={"name": "Orest", "kind": "cat"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_pet_requires_auth(self, client: AsyncClient):
        """Should return 401 when no auth token provided."""
        response = await client.get(
            f"/api/v1/pets/{TEST_PET_ID}?family_id={TEST_FAMILY_ID}"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_update_pet_requires_auth(self, client: AsyncClient):
        """Should return 401 when no auth token provided."""
        response = await client.patch(
            f"/api/v1/pets/{TEST_PET_ID}?family_id={TEST_FAMILY_ID}",
            json={"name": "New Name"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_delete_pet_requires_auth(self, client: AsyncClient):
        """Should return 401 when no auth token provided."""
        response = await client.delete(
            f"/api/v1/pets/{TEST_PET_ID}?family_id={TEST_FAMILY_ID}"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPetAccessControl:
    """Tests for access control on pet endpoints."""

    @pytest.mark.asyncio
    async def test_list_pets_no_family_access(
        self, client: AsyncClient, mock_db_session, auth_headers
    ):
        """Should return 403 when user doesn't belong to family."""
        mock_db_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        response = await client.get(
            f"/api/v1/pets?family_id={TEST_OTHER_FAMILY_ID}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_pet_no_family_access(
        self, client: AsyncClient, mock_db_session, auth_headers
    ):
        """Should return 403 when user doesn't belong to family."""
        mock_db_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        response = await client.post(
            f"/api/v1/pets?family_id={TEST_OTHER_FAMILY_ID}",
            headers=auth_headers,
            json={"name": "Orest", "kind": "cat"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestPetNotFound:
    """Tests for pet not found scenarios."""

    @pytest.mark.asyncio
    async def test_get_pet_not_found(
        self, client: AsyncClient, mock_db_session, auth_headers
    ):
        """Should return 404 when pet doesn't exist."""
        mock_db_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        response = await client.get(
            f"/api/v1/pets/{uuid4()}?family_id={TEST_FAMILY_ID}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_update_pet_not_found(
        self, client: AsyncClient, mock_db_session, auth_headers
    ):
        """Should return 404 when pet doesn't exist."""
        mock_db_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        response = await client.patch(
            f"/api/v1/pets/{uuid4()}?family_id={TEST_FAMILY_ID}",
            headers=auth_headers,
            json={"name": "New Name"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_pet_not_found(
        self, client: AsyncClient, mock_db_session, auth_headers
    ):
        """Should return 404 when pet doesn't exist."""
        mock_db_session.execute.return_value = MagicMock(
            scalar_one_or_none=MagicMock(return_value=None)
        )

        response = await client.delete(
            f"/api/v1/pets/{uuid4()}?family_id={TEST_FAMILY_ID}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestListPets:
    """Tests for listing pets."""

    @pytest.mark.asyncio
    async def test_list_pets_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return list of pets for the family."""
        # Mock access verification
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Create mock pets
        mock_pet1 = create_mock_pet(family_id=test_family_id, name="Buddy", kind="dog")
        mock_pet1.created_at = datetime.now(UTC)
        mock_pet1.current_weight = 25.5
        mock_pet1.photo_url = None
        mock_pet1.date_of_birth = None
        mock_pet1.created_by = UUID(test_user_id)

        mock_pet2 = create_mock_pet(family_id=test_family_id, name="Whiskers", kind="cat")
        mock_pet2.created_at = datetime.now(UTC)
        mock_pet2.current_weight = 10.0
        mock_pet2.photo_url = None
        mock_pet2.date_of_birth = None
        mock_pet2.created_by = UUID(test_user_id)

        # Setup mock query result for pets list
        pets_result = MagicMock()
        pets_result.scalars.return_value.all.return_value = [mock_pet1, mock_pet2]

        setup_family_access_verification(
            mock_db_session,
            mock_membership,
            additional_results=[pets_result]
        )

        # Patch cache functions
        with patch("app.api.endpoints.pets.cache_get", return_value=None), \
             patch("app.api.endpoints.pets.cache_set"):
            response = await client.get(
                f"/api/v1/pets?family_id={test_family_id}",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "pets" in data
        assert len(data["pets"]) == 2
        assert data["pets"][0]["name"] == "Buddy"
        assert data["pets"][1]["name"] == "Whiskers"

    @pytest.mark.asyncio
    async def test_list_pets_missing_family_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 400 when family_id is missing."""
        response = await client.get(
            "/api/v1/pets",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "family_id" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_list_pets_returns_cached_data(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return cached pets when available."""
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_family_access_verification(mock_db_session, mock_membership)

        # Import the actual schema to create a proper cached response
        from app.schemas.pet import PetListResponse, PetResponse

        pet_id = uuid4()
        cached_response = PetListResponse(pets=[
            PetResponse(
                id=pet_id,
                family_id=UUID(test_family_id),
                name="CachedPet",
                kind="cat",
                created_at=datetime.now(UTC),
                current_weight=5.0,
                photo_url=None,
                date_of_birth=None,
                created_by=UUID(test_user_id),
            )
        ])

        with patch("app.api.endpoints.pets.cache_get") as mock_cache_get:
            mock_cache_get.return_value = cached_response

            response = await client.get(
                f"/api/v1/pets?family_id={test_family_id}",
                headers=auth_headers,
            )

        # cache_get should have been called
        mock_cache_get.assert_called_once()
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["pets"]) == 1
        assert data["pets"][0]["name"] == "CachedPet"


class TestCreatePet:
    """Tests for creating pets."""

    @pytest.mark.asyncio
    async def test_create_pet_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create a pet successfully."""
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_family_access_verification(mock_db_session, mock_membership)

        # Mock refresh to set created attributes
        async def mock_refresh(obj):
            obj.id = uuid4()
            obj.created_at = datetime.now(UTC)
            obj.created_by = UUID(test_user_id)

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change"):
            response = await client.post(
                f"/api/v1/pets?family_id={test_family_id}",
                json={
                    "name": "Orest",
                    "kind": "cat",
                    "current_weight": 12.5,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Orest"
        assert data["kind"] == "cat"
        assert data["current_weight"] == 12.5
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_pet_with_date_of_birth(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create a pet with date of birth."""
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_family_access_verification(mock_db_session, mock_membership)

        dob = datetime(2020, 5, 15, tzinfo=UTC)

        async def mock_refresh(obj):
            obj.id = uuid4()
            obj.created_at = datetime.now(UTC)
            obj.created_by = UUID(test_user_id)
            obj.date_of_birth = dob

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change"):
            response = await client.post(
                f"/api/v1/pets?family_id={test_family_id}",
                json={
                    "name": "Luna",
                    "kind": "dog",
                    "date_of_birth": dob.isoformat(),
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Luna"
        assert data["date_of_birth"] is not None

    @pytest.mark.asyncio
    async def test_create_pet_invalidates_cache(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should invalidate pets cache after creation."""
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_family_access_verification(mock_db_session, mock_membership)

        async def mock_refresh(obj):
            obj.id = uuid4()
            obj.created_at = datetime.now(UTC)
            obj.created_by = UUID(test_user_id)

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.cache_delete") as mock_cache_delete, \
             patch("app.api.endpoints.pets.notify_family_pet_change"):
            response = await client.post(
                f"/api/v1/pets?family_id={test_family_id}",
                json={"name": "Rex", "kind": "dog"},
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED
        mock_cache_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_pet_sends_notification(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should notify family members after pet creation."""
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_family_access_verification(mock_db_session, mock_membership)

        async def mock_refresh(obj):
            obj.id = uuid4()
            obj.created_at = datetime.now(UTC)
            obj.created_by = UUID(test_user_id)

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change") as mock_notify:
            response = await client.post(
                f"/api/v1/pets?family_id={test_family_id}",
                json={"name": "Max", "kind": "dog"},
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED
        mock_notify.assert_called_once()


class TestGetPet:
    """Tests for getting a single pet."""

    @pytest.mark.asyncio
    async def test_get_pet_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return a pet by ID."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id, name="Buddy")
        mock_pet.created_at = datetime.now(UTC)
        mock_pet.current_weight = 25.5
        mock_pet.photo_url = None
        mock_pet.date_of_birth = None
        mock_pet.created_by = UUID(test_user_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        response = await client.get(
            f"/api/v1/pets/{pet_id}?family_id={test_family_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == pet_id
        assert data["name"] == "Buddy"
        assert data["kind"] == "dog"


class TestUpdatePet:
    """Tests for updating pets."""

    @pytest.mark.asyncio
    async def test_update_pet_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update a pet successfully."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id, name="OldName")
        mock_pet.created_at = datetime.now(UTC)
        mock_pet.current_weight = 25.5
        mock_pet.photo_url = None
        mock_pet.date_of_birth = None
        mock_pet.created_by = UUID(test_user_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        async def mock_refresh(obj):
            obj.name = "NewName"

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change"):
            response = await client.patch(
                f"/api/v1/pets/{pet_id}?family_id={test_family_id}",
                json={"name": "NewName"},
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_pet_weight(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update a pet's weight."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id)
        mock_pet.created_at = datetime.now(UTC)
        mock_pet.current_weight = 25.5
        mock_pet.photo_url = None
        mock_pet.date_of_birth = None
        mock_pet.created_by = UUID(test_user_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        async def mock_refresh(obj):
            obj.current_weight = 30.0

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change"):
            response = await client.patch(
                f"/api/v1/pets/{pet_id}?family_id={test_family_id}",
                json={"current_weight": 30.0},
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_update_pet_invalidates_cache(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should invalidate cache after update."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id)
        mock_pet.created_at = datetime.now(UTC)
        mock_pet.current_weight = 25.5
        mock_pet.photo_url = None
        mock_pet.date_of_birth = None
        mock_pet.created_by = UUID(test_user_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        mock_db_session.refresh = AsyncMock()

        with patch("app.api.endpoints.pets.cache_delete") as mock_cache_delete, \
             patch("app.api.endpoints.pets.notify_family_pet_change"):
            response = await client.patch(
                f"/api/v1/pets/{pet_id}?family_id={test_family_id}",
                json={"name": "UpdatedName"},
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        mock_cache_delete.assert_called_once()


class TestDeletePet:
    """Tests for deleting pets."""

    @pytest.mark.asyncio
    async def test_delete_pet_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete a pet successfully."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id, name="ToDelete")
        mock_pet.photo_url = None
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        with patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change"):
            response = await client.delete(
                f"/api/v1/pets/{pet_id}?family_id={test_family_id}",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_db_session.delete.assert_called_once_with(mock_pet)
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_delete_pet_with_photo_cleans_up_storage(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete pet photo from storage."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id)
        mock_pet.photo_url = "https://storage.example.com/pets/photo.jpg"
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        with patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change"), \
             patch("app.api.endpoints.pets.storage_service") as mock_storage:
            mock_storage.delete_image = AsyncMock(return_value=True)

            response = await client.delete(
                f"/api/v1/pets/{pet_id}?family_id={test_family_id}",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_storage.delete_image.assert_called_once_with(mock_pet.photo_url)

    @pytest.mark.asyncio
    async def test_delete_pet_sends_notification(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should notify family members after pet deletion."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id, name="DeletedPet")
        mock_pet.photo_url = None
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        with patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change") as mock_notify:
            response = await client.delete(
                f"/api/v1/pets/{pet_id}?family_id={test_family_id}",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        mock_notify.assert_called_once()


class TestHealthRecords:
    """Tests for pet health records."""

    @pytest.mark.asyncio
    async def test_create_health_record_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should create a health record successfully."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id)
        mock_pet.current_weight = 25.0
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        # Mock db.get for updating pet weight
        mock_db_session.get = AsyncMock(return_value=mock_pet)

        async def mock_refresh(obj):
            obj.id = uuid4()
            obj.recorded_at = datetime.now(UTC)

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.cache_delete"):
            response = await client.post(
                f"/api/v1/pets/{pet_id}/health-records",
                json={
                    "weight_pounds": 26.5,
                    "notes": "Regular checkup",
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["weight_pounds"] == 26.5
        assert data["notes"] == "Regular checkup"

    @pytest.mark.asyncio
    async def test_create_health_record_updates_pet_weight(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should update pet's current weight when recording weight."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id)
        mock_pet.current_weight = 25.0
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_pet_access_verification(mock_db_session, mock_pet, mock_membership)

        mock_db_session.get = AsyncMock(return_value=mock_pet)

        async def mock_refresh(obj):
            obj.id = uuid4()
            obj.recorded_at = datetime.now(UTC)

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.cache_delete") as mock_cache:
            response = await client.post(
                f"/api/v1/pets/{pet_id}/health-records",
                json={"weight_pounds": 28.0},
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED
        # Pet weight should be updated
        assert mock_pet.current_weight == 28.0
        # Cache should be invalidated
        mock_cache.assert_called()

    @pytest.mark.asyncio
    async def test_list_health_records_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should list health records for a pet."""
        pet_id = str(uuid4())
        mock_pet = create_mock_pet(pet_id=pet_id, family_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Create mock health records
        mock_record1 = MagicMock()
        mock_record1.id = uuid4()
        mock_record1.pet_id = UUID(pet_id)
        mock_record1.weight_pounds = 25.0
        mock_record1.age_years = 2
        mock_record1.notes = "First checkup"
        mock_record1.recorded_at = datetime.now(UTC)

        mock_record2 = MagicMock()
        mock_record2.id = uuid4()
        mock_record2.pet_id = UUID(pet_id)
        mock_record2.weight_pounds = 26.0
        mock_record2.age_years = 3
        mock_record2.notes = "Second checkup"
        mock_record2.recorded_at = datetime.now(UTC)

        # Setup mock query result
        records_result = MagicMock()
        records_result.scalars.return_value.all.return_value = [mock_record1, mock_record2]

        setup_pet_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[records_result]
        )

        response = await client.get(
            f"/api/v1/pets/{pet_id}/health-records",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["weight_pounds"] == 25.0
        assert data[1]["weight_pounds"] == 26.0


class TestPhotoUrlValidation:
    """Tests for photo URL validation."""

    @pytest.mark.asyncio
    async def test_create_pet_with_invalid_photo_url_domain(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should reject photo URL from external domain when storage is configured."""
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_family_access_verification(mock_db_session, mock_membership)

        with patch("app.api.endpoints.pets.storage_service") as mock_storage:
            mock_storage.is_configured = True
            mock_storage.settings.s3_public_url = "https://storage.example.com"

            response = await client.post(
                f"/api/v1/pets?family_id={test_family_id}",
                json={
                    "name": "Test",
                    "kind": "cat",
                    "photo_url": "https://evil.com/malicious.jpg",
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "photo" in response.json()["detail"].lower() or "storage" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_pet_with_wrong_family_photo_url(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should reject photo URL that belongs to different family."""
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_family_access_verification(mock_db_session, mock_membership)

        other_family_id = str(uuid4())

        with patch("app.api.endpoints.pets.storage_service") as mock_storage:
            mock_storage.is_configured = True
            mock_storage.settings.s3_public_url = "https://storage.example.com"

            response = await client.post(
                f"/api/v1/pets?family_id={test_family_id}",
                json={
                    "name": "Test",
                    "kind": "cat",
                    "photo_url": f"https://storage.example.com/pets/{other_family_id}/photo.jpg",
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "different family" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_pet_allows_any_url_when_storage_not_configured(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should allow any photo URL when storage is not configured (dev mode)."""
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        setup_family_access_verification(mock_db_session, mock_membership)

        async def mock_refresh(obj):
            obj.id = uuid4()
            obj.created_at = datetime.now(UTC)
            obj.created_by = UUID(test_user_id)

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.pets.storage_service") as mock_storage, \
             patch("app.api.endpoints.pets.cache_delete"), \
             patch("app.api.endpoints.pets.notify_family_pet_change"):
            mock_storage.is_configured = False

            response = await client.post(
                f"/api/v1/pets?family_id={test_family_id}",
                json={
                    "name": "Test",
                    "kind": "cat",
                    "photo_url": "https://any-url.com/photo.jpg",
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_201_CREATED
