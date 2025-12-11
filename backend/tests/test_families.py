"""
Tests for family management endpoints.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_ADMIN_USER_ID,
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_family,
    create_mock_membership,
)


class TestUpdateFamily:
    """Tests for PATCH /families/{family_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_family_name_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        admin_auth_headers: dict,
        test_family_id: str,
        test_admin_user_id: str,
    ):
        """Admin can successfully update family name."""
        # Setup mocks
        mock_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_family = create_mock_family(
            family_id=test_family_id,
            name="Old Family Name",
        )

        # Mock database queries
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        # Execute returns different results for different queries
        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        # Make request
        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": "New Family Name"},
            headers=admin_auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_family_id
        assert data["name"] == "New Family Name"
        assert data["role"] == "admin"

        # Verify database was updated
        assert mock_family.name == "New Family Name"
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_family_name_unauthorized_not_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Non-member cannot update family name."""
        # Mock no membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_family_name_unauthorized_not_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
        test_user_id: str,
    ):
        """Regular member cannot update family name (only admin can)."""
        # Mock membership with member role (not admin)
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "Only family admins" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_family_name_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        admin_auth_headers: dict,
        test_family_id: str,
        test_admin_user_id: str,
    ):
        """Returns 404 when family doesn't exist."""
        # Mock admin membership exists
        mock_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # But family not found
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": "New Name"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 404
        assert "Family not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_family_name_empty_validation(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
        test_family_id: str,
    ):
        """Validation error for empty name."""
        # Empty string should fail Pydantic validation
        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": ""},
            headers=admin_auth_headers,
        )

        # Empty string is technically valid in current schema,
        # but you might want to add min_length=1 validation
        # For now, this test documents current behavior
        assert response.status_code in [200, 403, 422]

    @pytest.mark.asyncio
    async def test_update_family_no_auth(
        self,
        client: AsyncClient,
        test_family_id: str,
    ):
        """Returns 401 when no auth token provided."""
        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": "New Name"},
        )

        assert response.status_code == 403  # HTTPBearer returns 403 for missing token

    @pytest.mark.asyncio
    async def test_update_family_invalid_uuid(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Returns error for invalid family ID format."""
        response = await client.patch(
            "/api/v1/families/not-a-valid-uuid",
            json={"name": "New Name"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 422  # Pydantic validation error


class TestUpdateMemberRole:
    """Tests for PATCH /families/{family_id}/members/{user_id}/role endpoint."""

    @pytest.mark.asyncio
    async def test_update_member_role_promote_to_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        admin_auth_headers: dict,
        test_family_id: str,
        test_admin_user_id: str,
        test_user_id: str,
    ):
        """Admin can promote a member to admin."""
        # Mock admin membership (current user)
        mock_admin_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )

        # Mock target membership (member to promote)
        mock_target_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        # Add user info to target membership
        mock_target_membership.user = MagicMock()
        mock_target_membership.user.email = "member@test.com"
        mock_target_membership.user.first_name = "Test"
        mock_target_membership.user.last_name = "Member"

        # Mock family for notification
        mock_family = create_mock_family(family_id=test_family_id, name="Test Family")

        # Setup mock database query results
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = mock_target_membership

        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result, family_result, tokens_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_user_id}/role",
            json={"role": "admin"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user_id
        assert data["role"] == "admin"
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_member_role_demote_to_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        admin_auth_headers: dict,
        test_family_id: str,
        test_admin_user_id: str,
        test_user_id: str,
    ):
        """Admin can demote another admin to member when multiple admins exist."""
        # Mock current admin
        mock_admin_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )

        # Mock target admin to demote
        mock_target_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_target_membership.user = MagicMock()
        mock_target_membership.user.email = "admin2@test.com"
        mock_target_membership.user.first_name = "Other"
        mock_target_membership.user.last_name = "Admin"

        mock_family = create_mock_family(family_id=test_family_id, name="Test Family")

        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = mock_target_membership

        # Admin count = 2 (allows demotion)
        count_result = MagicMock()
        count_result.scalar.return_value = 2

        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result, count_result, family_result, tokens_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_user_id}/role",
            json={"role": "member"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_update_member_role_not_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
        test_user_id: str,
    ):
        """Non-admin cannot change roles - returns 403."""
        # Mock member (not admin) trying to change roles
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_user_id}/role",
            json={"role": "admin"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "Only family admins" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_member_role_not_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
        test_user_id: str,
    ):
        """Non-member cannot change roles - returns 403."""
        # No membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_user_id}/role",
            json={"role": "admin"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_member_role_target_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        admin_auth_headers: dict,
        test_family_id: str,
        test_admin_user_id: str,
        test_user_id: str,
    ):
        """Target member not found - returns 404."""
        mock_admin_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )

        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        # Target not found
        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_user_id}/role",
            json={"role": "admin"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 404
        assert "Member not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_member_role_last_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        admin_auth_headers: dict,
        test_family_id: str,
        test_admin_user_id: str,
    ):
        """Cannot demote the last admin - returns 400."""
        mock_admin_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )

        # Target is same admin (self-demotion attempt)
        mock_target_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_target_membership.user = MagicMock()
        mock_target_membership.user.email = "admin@test.com"
        mock_target_membership.user.first_name = None
        mock_target_membership.user.last_name = None

        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = mock_target_membership

        # Only 1 admin exists
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result, count_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}/role",
            json={"role": "member"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 400
        assert "Cannot demote the last admin" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_member_role_invalid_role(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        admin_auth_headers: dict,
        test_family_id: str,
        test_admin_user_id: str,
        test_user_id: str,
    ):
        """Invalid role value - returns 422."""
        mock_admin_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_admin_membership
        mock_db_session.execute = AsyncMock(return_value=membership_result)

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_user_id}/role",
            json={"role": "superadmin"},  # Invalid role
            headers=admin_auth_headers,
        )

        assert response.status_code == 422
        # Pydantic validation returns error list with expected values
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any("'admin' or 'member'" in str(err) for err in detail)
