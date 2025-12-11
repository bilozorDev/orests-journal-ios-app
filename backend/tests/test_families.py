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
        mock_db_session: AsyncMock,
        admin_auth_headers: dict,
        test_family_id: str,
        test_admin_user_id: str,
    ):
        """Empty string is accepted (no min_length validation currently)."""
        # Setup mocks for admin membership check and family update
        mock_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_family = create_mock_family(
            family_id=test_family_id,
            name="Old Family Name",
        )

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": ""},
            headers=admin_auth_headers,
        )

        # Empty string is technically valid in current schema (no min_length)
        # This documents current behavior - consider adding min_length=1
        assert response.status_code == 200

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

        # HTTPBearer returns 401 Unauthorized for missing token
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_family_invalid_uuid(
        self,
        client: AsyncClient,
        admin_auth_headers: dict,
    ):
        """Invalid UUID returns 422 Unprocessable Entity."""
        response = await client.patch(
            "/api/v1/families/not-a-valid-uuid",
            json={"name": "New Name"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 422
        assert "Invalid family_id format" in response.json()["detail"]


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


class TestBruteForceProtection:
    """Tests for invite code brute force protection."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_after_failure(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """User must wait after a failed attempt due to backoff."""
        from datetime import datetime, timedelta

        # Create mock user with 1 failed attempt that just happened
        mock_user = MagicMock()
        mock_user.id = test_user_id
        mock_user.is_locked_out = False
        mock_user.lockout_expires_at = None
        mock_user.failed_invite_attempts = 1
        mock_user.last_failed_invite_at = datetime.utcnow()  # Just happened

        # Mock lockout check - user not locked
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        mock_db_session.execute = AsyncMock(return_value=user_result)

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "WRONGCODE"},
            headers=auth_headers,
        )

        # Should be blocked by backoff
        assert response.status_code == 429
        assert "wait" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_account_lockout_after_threshold(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Account is locked after 10 consecutive failures."""
        from datetime import datetime, timedelta

        # Create mock user that is locked out
        mock_user = MagicMock()
        mock_user.id = test_user_id
        mock_user.is_locked_out = True
        mock_user.lockout_expires_at = datetime.utcnow() + timedelta(minutes=30)
        mock_user.failed_invite_attempts = 10
        mock_user.last_failed_invite_at = datetime.utcnow()

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        mock_db_session.execute = AsyncMock(return_value=user_result)

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "ANYCODE12"},
            headers=auth_headers,
        )

        # Should be blocked by lockout
        assert response.status_code == 403
        assert "locked" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_lockout_expires_allows_retry(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Expired lockout allows user to try again."""
        from datetime import datetime, timedelta

        # Create mock user with expired lockout
        mock_user = MagicMock()
        mock_user.id = test_user_id
        mock_user.is_locked_out = True
        mock_user.lockout_expires_at = datetime.utcnow() - timedelta(minutes=1)  # Expired
        mock_user.failed_invite_attempts = 10
        mock_user.last_failed_invite_at = datetime.utcnow() - timedelta(hours=2)

        # Family that will be found
        mock_family = create_mock_family(
            family_id=test_family_id,
            invite_code="VALIDCOD",
        )

        # Mock membership - user not yet a member
        mock_membership = None

        # Setup mock query results
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = mock_membership

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        # Multiple execute calls for different queries
        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result,   # check_user_lockout - finds user, clears expired lockout
                user_result,   # check_exponential_backoff - cleared, no backoff
                count_result,  # check_rate_limit - user count
                count_result,  # check_rate_limit - IP count
                family_result, # find family by code
                existing_result, # check existing membership
                user_result,   # log_invite_attempt commit
                user_result,   # handle_successful_invite_attempt
                user_result,   # get new_user for notification
                tokens_result, # get other family member tokens
            ]
        )

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "VALIDCOD"},
            headers=auth_headers,
        )

        # Should succeed after lockout expires
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_successful_attempt_allowed_without_backoff(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """User with no failed attempts can join immediately."""
        from datetime import datetime

        # Create mock user with no failed attempts
        mock_user = MagicMock()
        mock_user.id = test_user_id
        mock_user.is_locked_out = False
        mock_user.lockout_expires_at = None
        mock_user.failed_invite_attempts = 0
        mock_user.last_failed_invite_at = None

        mock_family = create_mock_family(
            family_id=test_family_id,
            invite_code="GOODCODE",
        )

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result,   # check_user_lockout
                user_result,   # check_exponential_backoff
                count_result,  # check_rate_limit - user
                count_result,  # check_rate_limit - IP
                family_result, # find family
                existing_result, # check existing membership
                user_result,   # log_invite_attempt
                user_result,   # handle_successful_invite
                user_result,   # get user for notification
                tokens_result, # get tokens
            ]
        )

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "GOODCODE"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["family"]["id"] == test_family_id
