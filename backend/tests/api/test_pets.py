"""Tests for pets API endpoints.

Tests cover:
- Authorization checks (no auth, wrong family)
- Basic validation errors
"""
import pytest
from unittest.mock import MagicMock
from uuid import uuid4

from httpx import AsyncClient
from fastapi import status

from tests.conftest import TEST_FAMILY_ID


# Test data
TEST_PET_ID = uuid4()
TEST_OTHER_FAMILY_ID = uuid4()


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
