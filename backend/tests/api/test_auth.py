"""
Comprehensive integration tests for authentication endpoints.

Tests cover:
- POST /api/v1/auth/apple - Sign in with Apple
- GET /api/v1/auth/me - Get current user info
- PATCH /api/v1/auth/profile - Update user profile
- DELETE /api/v1/auth/account - Delete user account
- POST /api/v1/auth/test-login - Test login (dev/test only)
- DELETE /api/v1/auth/test-cleanup/{test_user_id} - Test cleanup (dev/test only)

Test scenarios:
- Happy path (200, 201 responses)
- Validation errors (422)
- Unauthorized (401)
- Not found (404)
- Bad request (400)
- Forbidden (403)
- Token validation
- Family membership scenarios
- Cache invalidation
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    TEST_ADMIN_USER_ID,
    create_mock_family,
    create_mock_membership,
)


# Helper to create mock user
def create_mock_user(
    user_id: str = None,
    apple_user_id: str = "apple_123456",
    email: str = "test@example.com",
    first_name: str = "John",
    last_name: str = "Doe",
):
    """Create a mock User object."""
    user = MagicMock()
    user.id = UUID(user_id) if user_id else uuid4()
    user.apple_user_id = apple_user_id
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.created_at = datetime.utcnow()
    return user


# Helper to create mock device token
def create_mock_device_token(
    device_token: str = "device_token_123",
    user_id: str = None,
    is_active: bool = True,
):
    """Create a mock UserDeviceToken object."""
    token = MagicMock()
    token.device_token = device_token
    token.user_id = UUID(user_id) if user_id else uuid4()
    token.is_active = is_active
    return token


class TestSignInWithApple:
    """Tests for POST /api/v1/auth/apple endpoint."""

    @pytest.mark.asyncio
    async def test_sign_in_new_user(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should create new user and return auth response."""
        # Mock Apple token verification
        mock_apple_claims = {
            "sub": "apple_user_123",
            "email": "newuser@example.com",
        }

        mock_user = create_mock_user(
            user_id=str(uuid4()),
            apple_user_id="apple_user_123",
            email="newuser@example.com",
            first_name="Jane",
            last_name="Smith",
        )

        # Mock database queries - user not found, then created
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result]
        )

        # Mock refresh to set created user attributes
        async def mock_refresh(obj):
            obj.id = mock_user.id
            obj.created_at = mock_user.created_at

        mock_db_session.refresh = mock_refresh

        with patch(
            "app.api.endpoints.auth.verify_apple_identity_token",
            return_value=mock_apple_claims,
        ):
            # Make request
            response = await client.post(
                "/api/v1/auth/apple",
                json={
                    "identity_token": "fake_apple_token",
                    "user_id": "apple_user_123",
                    "email": "newuser@example.com",
                    "first_name": "Jane",
                    "last_name": "Smith",
                },
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "token" in data
            assert data["user"]["email"] == "newuser@example.com"
            assert data["user"]["first_name"] == "Jane"
            assert data["user"]["last_name"] == "Smith"
            assert data["families"] == []

            # Verify user was created
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_sign_in_existing_user(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        test_family_id: str,
    ):
        """Should return existing user and their families."""
        mock_apple_claims = {
            "sub": "apple_user_existing",
            "email": "existing@example.com",
        }

        mock_user = create_mock_user(
            user_id=str(uuid4()),
            apple_user_id="apple_user_existing",
            email="existing@example.com",
            first_name="Existing",
            last_name="User",
        )

        mock_family = create_mock_family(
            family_id=test_family_id,
            name="Existing Family",
        )
        mock_membership = create_mock_membership(
            user_id=str(mock_user.id),
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.family = mock_family

        # Mock database queries - user found
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [mock_membership]

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result]
        )

        with patch(
            "app.api.endpoints.auth.verify_apple_identity_token",
            return_value=mock_apple_claims,
        ):
            response = await client.post(
                "/api/v1/auth/apple",
                json={
                    "identity_token": "fake_apple_token",
                    "user_id": "apple_user_existing",
                },
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "token" in data
            assert data["user"]["email"] == "existing@example.com"
            assert len(data["families"]) == 1
            assert data["families"][0]["id"] == test_family_id
            assert data["families"][0]["name"] == "Existing Family"
            assert data["families"][0]["role"] == "admin"

            # Verify no new user was created
            mock_db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_sign_in_update_existing_user_info(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should update user info when Apple provides it (first sign-in scenario)."""
        mock_apple_claims = {
            "sub": "apple_user_update",
            "email": "update@example.com",
        }

        # Existing user without name
        mock_user = create_mock_user(
            user_id=str(uuid4()),
            apple_user_id="apple_user_update",
            email=None,  # No email yet
            first_name=None,  # No name yet
            last_name=None,
        )

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result]
        )

        with patch(
            "app.api.endpoints.auth.verify_apple_identity_token",
            return_value=mock_apple_claims,
        ):
            response = await client.post(
                "/api/v1/auth/apple",
                json={
                    "identity_token": "fake_apple_token",
                    "user_id": "apple_user_update",
                    "email": "update@example.com",
                    "first_name": "Updated",
                    "last_name": "Name",
                },
            )

            # Verify response
            assert response.status_code == 200

            # Verify user info was updated
            assert mock_user.email == "update@example.com"
            assert mock_user.first_name == "Updated"
            assert mock_user.last_name == "Name"
            mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_sign_in_invalid_apple_token(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should return 401 when Apple token is invalid."""
        from fastapi import HTTPException, status

        # Mock Apple token verification failure
        with patch(
            "app.api.endpoints.auth.verify_apple_identity_token",
            side_effect=HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Apple token",
            ),
        ):
            response = await client.post(
                "/api/v1/auth/apple",
                json={
                    "identity_token": "invalid_token",
                    "user_id": "some_user",
                },
            )

            # Verify error response
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_sign_in_missing_apple_user_id(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should return 400 when Apple token doesn't contain user ID."""
        # Mock Apple claims without 'sub' (user ID)
        mock_apple_claims = {
            "email": "test@example.com",
            # Missing "sub" field
        }

        with patch(
            "app.api.endpoints.auth.verify_apple_identity_token",
            return_value=mock_apple_claims,
        ):
            response = await client.post(
                "/api/v1/auth/apple",
                json={
                    "identity_token": "fake_token",
                    "user_id": "some_user",
                },
            )

            # Verify error response
            assert response.status_code == 400
            assert "missing user ID" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_sign_in_validation_missing_identity_token(
        self,
        client: AsyncClient,
    ):
        """Should return 422 when identity_token is missing."""
        response = await client.post(
            "/api/v1/auth/apple",
            json={
                "user_id": "some_user",
                # Missing identity_token
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_sign_in_validation_missing_user_id(
        self,
        client: AsyncClient,
    ):
        """Should return 422 when user_id is missing."""
        response = await client.post(
            "/api/v1/auth/apple",
            json={
                "identity_token": "fake_token",
                # Missing user_id
            },
        )

        assert response.status_code == 422


class TestGetCurrentUser:
    """Tests for GET /api/v1/auth/me endpoint."""

    @pytest.mark.asyncio
    async def test_get_me_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return current user info and families."""
        mock_user = create_mock_user(
            user_id=test_user_id,
            email="me@example.com",
            first_name="Current",
            last_name="User",
        )

        mock_family = create_mock_family(
            family_id=test_family_id,
            name="My Family",
        )
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_membership.family = mock_family

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [mock_membership]

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result]
        )

        # Make request
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["id"] == test_user_id
        assert data["user"]["email"] == "me@example.com"
        assert data["user"]["first_name"] == "Current"
        assert len(data["families"]) == 1
        assert data["families"][0]["id"] == test_family_id
        assert data["families"][0]["role"] == "member"

    @pytest.mark.asyncio
    async def test_get_me_multiple_families(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return all families user belongs to."""
        mock_user = create_mock_user(user_id=test_user_id)

        family_1_id = str(uuid4())
        family_2_id = str(uuid4())

        mock_family_1 = create_mock_family(family_id=family_1_id, name="Family 1")
        mock_family_2 = create_mock_family(family_id=family_2_id, name="Family 2")

        mock_membership_1 = create_mock_membership(
            user_id=test_user_id, family_id=family_1_id, role="admin"
        )
        mock_membership_1.family = mock_family_1

        mock_membership_2 = create_mock_membership(
            user_id=test_user_id, family_id=family_2_id, role="member"
        )
        mock_membership_2.family = mock_family_2

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [
            mock_membership_1,
            mock_membership_2,
        ]

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result]
        )

        # Make request
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data["families"]) == 2
        assert data["families"][0]["id"] == family_1_id
        assert data["families"][0]["role"] == "admin"
        assert data["families"][1]["id"] == family_2_id
        assert data["families"][1]["role"] == "member"

    @pytest.mark.asyncio
    async def test_get_me_no_families(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return empty families list when user has no families."""
        mock_user = create_mock_user(user_id=test_user_id)

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result]
        )

        # Make request
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["families"] == []

    @pytest.mark.asyncio
    async def test_get_me_user_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when user doesn't exist in database."""
        # Mock user not found
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=user_result)

        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_me_unauthorized_no_token(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_unauthorized_invalid_token(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when invalid auth token provided."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401


class TestUpdateProfile:
    """Tests for PATCH /api/v1/auth/profile endpoint."""

    @pytest.mark.asyncio
    async def test_update_profile_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should update user profile successfully."""
        mock_user = create_mock_user(
            user_id=test_user_id,
            first_name="Old",
            last_name="Name",
        )

        # Mock database query
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=user_result)

        # Make request
        response = await client.patch(
            "/api/v1/auth/profile",
            json={
                "first_name": "New",
                "last_name": "Updated",
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "New"
        assert data["last_name"] == "Updated"

        # Verify user was updated
        assert mock_user.first_name == "New"
        assert mock_user.last_name == "Updated"
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_profile_first_name_only(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should update only first_name when last_name not provided."""
        mock_user = create_mock_user(
            user_id=test_user_id,
            first_name="Old",
            last_name="Original",
        )

        # Mock database query
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=user_result)

        # Make request with only first_name
        response = await client.patch(
            "/api/v1/auth/profile",
            json={"first_name": "NewFirst"},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        assert mock_user.first_name == "NewFirst"
        # last_name should remain unchanged (stays as "Original")

    @pytest.mark.asyncio
    async def test_update_profile_with_both_names(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should update both first_name and last_name."""
        mock_user = create_mock_user(
            user_id=test_user_id,
            first_name="Old",
            last_name="Name",
        )

        # Mock database query
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=user_result)

        # Make request with both names
        response = await client.patch(
            "/api/v1/auth/profile",
            json={
                "first_name": "New",
                "last_name": "LastName",
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        assert mock_user.first_name == "New"
        assert mock_user.last_name == "LastName"

    @pytest.mark.asyncio
    async def test_update_profile_user_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when user doesn't exist."""
        # Mock user not found
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=user_result)

        response = await client.patch(
            "/api/v1/auth/profile",
            json={"first_name": "New"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_profile_validation_missing_first_name(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when first_name is missing."""
        response = await client.patch(
            "/api/v1/auth/profile",
            json={"last_name": "Last"},  # Missing required first_name
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_profile_unauthorized_no_token(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        response = await client.patch(
            "/api/v1/auth/profile",
            json={"first_name": "New"},
        )

        assert response.status_code == 401


class TestDeleteAccount:
    """Tests for DELETE /api/v1/auth/account endpoint."""

    @pytest.mark.asyncio
    async def test_delete_account_only_member_in_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete both user and family when user is only member."""
        mock_user = create_mock_user(
            user_id=test_user_id,
            first_name="Solo",
        )

        mock_family = create_mock_family(family_id=test_family_id)

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.family = mock_family

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [mock_membership]

        # Other admins count = 0
        admin_count_result = MagicMock()
        admin_count_result.scalar.return_value = 0

        # Other members count = 0
        member_count_result = MagicMock()
        member_count_result.scalar.return_value = 0

        # Device tokens query
        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result,
                membership_result,
                admin_count_result,
                member_count_result,
                tokens_result,
            ]
        )

        with patch("app.api.endpoints.auth.cache_delete") as mock_cache_delete:
            # Make request
            response = await client.delete(
                "/api/v1/auth/account",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert f"deleted_family_{test_family_id}" in data["steps_completed"]
            assert "deleted_device_tokens" in data["steps_completed"]
            assert "deleted_account" in data["steps_completed"]

            # Verify family was deleted
            assert mock_db_session.delete.call_count == 2  # Family + User
            mock_cache_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_account_with_other_admins(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should remove from family and notify admins when other admins exist."""
        mock_user = create_mock_user(
            user_id=test_user_id,
            first_name="Leaving",
        )

        mock_family = create_mock_family(
            family_id=test_family_id,
            name="Shared Family",
        )

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.family = mock_family

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [mock_membership]

        # Other admins count = 1
        admin_count_result = MagicMock()
        admin_count_result.scalar.return_value = 1

        # Other members count = 1
        member_count_result = MagicMock()
        member_count_result.scalar.return_value = 1

        # Admin tokens query
        admin_tokens_result = MagicMock()
        admin_tokens_result.scalars.return_value.all.return_value = [
            "admin_token_123"
        ]

        # Device tokens query
        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result,
                membership_result,
                admin_count_result,
                member_count_result,
                admin_tokens_result,  # get_admin_device_tokens: admin IDs
                admin_tokens_result,  # get_admin_device_tokens: device tokens
                tokens_result,
            ]
        )

        with patch("app.api.endpoints.auth.cache_delete"), patch(
            "app.api.endpoints.auth.apns_service.send_to_multiple"
        ) as mock_send_notification:
            # Make request
            response = await client.delete(
                "/api/v1/auth/account",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert f"removed_from_family_{test_family_id}" in data["steps_completed"]

            # Verify notification was sent
            mock_send_notification.assert_called_once()
            call_kwargs = mock_send_notification.call_args.kwargs
            assert "Leaving left" in call_kwargs["title"]
            assert call_kwargs["data"]["type"] == "account_deleted"

    @pytest.mark.asyncio
    async def test_delete_account_only_admin_requires_new_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when only admin and new_admin_user_id not provided."""
        mock_user = create_mock_user(user_id=test_user_id)

        mock_family = create_mock_family(
            family_id=test_family_id,
            name="Family Name",
        )

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.family = mock_family

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [mock_membership]

        # Other admins count = 0 (only admin)
        admin_count_result = MagicMock()
        admin_count_result.scalar.return_value = 0

        # Other members count = 2 (has other members)
        member_count_result = MagicMock()
        member_count_result.scalar.return_value = 2

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result, admin_count_result, member_count_result]
        )

        # Make request without new_admin_user_id
        response = await client.delete(
            "/api/v1/auth/account",
            headers=auth_headers,
        )

        # Verify error response
        assert response.status_code == 400
        assert "only admin" in response.json()["detail"]
        assert "select a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_account_promote_new_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should promote new admin before deleting account."""
        new_admin_id = str(uuid4())

        mock_user = create_mock_user(
            user_id=test_user_id,
            first_name="Departing",
        )

        mock_new_admin_user = create_mock_user(
            user_id=new_admin_id,
            first_name="NewAdmin",
        )

        mock_family = create_mock_family(family_id=test_family_id)

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.family = mock_family

        mock_new_admin_membership = create_mock_membership(
            user_id=new_admin_id,
            family_id=test_family_id,
            role="member",
        )
        mock_new_admin_membership.user = mock_new_admin_user

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [mock_membership]

        # Other admins count = 0
        admin_count_result = MagicMock()
        admin_count_result.scalar.return_value = 0

        # Other members count = 1
        member_count_result = MagicMock()
        member_count_result.scalar.return_value = 1

        # New admin membership query
        new_admin_result = MagicMock()
        new_admin_result.scalar_one_or_none.return_value = mock_new_admin_membership

        # Device tokens for new admin
        new_admin_tokens_result = MagicMock()
        new_admin_tokens_result.scalars.return_value.all.return_value = [
            "new_admin_token"
        ]

        # User device tokens
        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result,
                membership_result,
                admin_count_result,
                member_count_result,
                new_admin_result,
                new_admin_tokens_result,
                tokens_result,
            ]
        )

        with patch("app.api.endpoints.auth.cache_delete"), patch(
            "app.api.endpoints.auth.apns_service.send_to_multiple"
        ) as mock_send_notification:
            # Make request with new_admin_user_id
            import json
            response = await client.request(
                "DELETE",
                "/api/v1/auth/account",
                content=json.dumps({"new_admin_user_id": new_admin_id}),
                headers={**auth_headers, "Content-Type": "application/json"},
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert (
                f"promoted_admin_and_removed_{test_family_id}"
                in data["steps_completed"]
            )

            # Verify new admin was promoted
            assert mock_new_admin_membership.role == "admin"
            mock_db_session.flush.assert_called_once()

            # Verify notification sent to new admin
            mock_send_notification.assert_called_once()
            call_kwargs = mock_send_notification.call_args.kwargs
            assert "now an admin" in call_kwargs["title"]

    @pytest.mark.asyncio
    async def test_delete_account_invalid_new_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when new_admin_user_id is not a family member."""
        invalid_user_id = str(uuid4())

        mock_user = create_mock_user(user_id=test_user_id)

        mock_family = create_mock_family(family_id=test_family_id)

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.family = mock_family

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [mock_membership]

        admin_count_result = MagicMock()
        admin_count_result.scalar.return_value = 0

        member_count_result = MagicMock()
        member_count_result.scalar.return_value = 1

        # New admin membership not found
        new_admin_result = MagicMock()
        new_admin_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result,
                membership_result,
                admin_count_result,
                member_count_result,
                new_admin_result,
            ]
        )

        # Make request with invalid new_admin_user_id
        import json
        response = await client.request(
            "DELETE",
            "/api/v1/auth/account",
            content=json.dumps({"new_admin_user_id": invalid_user_id}),
            headers={**auth_headers, "Content-Type": "application/json"},
        )

        # Verify error response
        assert response.status_code == 400
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_account_cannot_select_self_as_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when trying to select self as new admin."""
        mock_user = create_mock_user(user_id=test_user_id)

        mock_family = create_mock_family(family_id=test_family_id)

        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.family = mock_family

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = [mock_membership]

        admin_count_result = MagicMock()
        admin_count_result.scalar.return_value = 0

        member_count_result = MagicMock()
        member_count_result.scalar.return_value = 1

        # New admin query - returns self
        new_admin_result = MagicMock()
        new_admin_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result,
                membership_result,
                admin_count_result,
                member_count_result,
                new_admin_result,
            ]
        )

        # Make request selecting self as new admin
        import json
        response = await client.request(
            "DELETE",
            "/api/v1/auth/account",
            content=json.dumps({"new_admin_user_id": test_user_id}),
            headers={**auth_headers, "Content-Type": "application/json"},
        )

        # Verify error response
        assert response.status_code == 400
        assert "cannot select yourself" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_account_user_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 404 when user doesn't exist."""
        # Mock user not found
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=user_result)

        response = await client.delete(
            "/api/v1/auth/account",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_delete_account_deletes_device_tokens(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should delete all user device tokens."""
        mock_user = create_mock_user(user_id=test_user_id)

        # Mock database queries
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = []

        # Mock device tokens
        mock_token_1 = create_mock_device_token(user_id=test_user_id)
        mock_token_2 = create_mock_device_token(user_id=test_user_id)

        tokens_result = MagicMock()
        tokens_result.scalars.return_value.all.return_value = [
            mock_token_1,
            mock_token_2,
        ]

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result, tokens_result]
        )

        # Make request
        response = await client.delete(
            "/api/v1/auth/account",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "deleted_device_tokens" in data["steps_completed"]

        # Verify tokens were deleted
        assert mock_db_session.delete.call_count == 3  # 2 tokens + user

    @pytest.mark.asyncio
    async def test_delete_account_unauthorized_no_token(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        response = await client.delete("/api/v1/auth/account")

        assert response.status_code == 401


class TestTestLogin:
    """Tests for POST /api/v1/auth/test-login endpoint (dev/test only)."""

    @pytest.mark.asyncio
    async def test_test_login_create_new_user(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should create test user and return auth response."""
        mock_user = create_mock_user(
            user_id=str(uuid4()),
            apple_user_id="test_ui-test-user",
            email="uitest@example.com",
            first_name="UI",
            last_name="Tester",
        )

        # Mock user not found, then created
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result]
        )

        # Mock refresh
        async def mock_refresh(obj):
            obj.id = mock_user.id
            obj.created_at = mock_user.created_at

        mock_db_session.refresh = mock_refresh

        # Make request
        response = await client.post(
            "/api/v1/auth/test-login",
            json={
                "test_user_id": "ui-test-user",
                "email": "uitest@example.com",
                "first_name": "UI",
                "last_name": "Tester",
            },
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["email"] == "uitest@example.com"
        assert data["user"]["first_name"] == "UI"

    @pytest.mark.asyncio
    async def test_test_login_existing_user(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should return existing test user."""
        mock_user = create_mock_user(
            user_id=str(uuid4()),
            apple_user_id="test_existing",
            email="existing@test.com",
        )

        # Mock existing user found
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, membership_result]
        )

        # Make request
        response = await client.post(
            "/api/v1/auth/test-login",
            json={"test_user_id": "existing"},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == "existing@test.com"

        # Verify no new user created
        mock_db_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_test_login_create_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should create family when create_family=True."""
        mock_user = create_mock_user(user_id=str(uuid4()))

        # Mock user not found
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None

        # Mock no existing family membership
        existing_membership_result = MagicMock()
        existing_membership_result.scalar_one_or_none.return_value = None

        # Mock final families query
        membership_result = MagicMock()
        membership_result.scalars.return_value.all.return_value = []

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result, existing_membership_result, membership_result]
        )

        # Mock refresh
        async def mock_refresh(obj):
            obj.id = mock_user.id
            obj.created_at = mock_user.created_at

        mock_db_session.refresh = mock_refresh

        # Make request with create_family=True
        response = await client.post(
            "/api/v1/auth/test-login",
            json={
                "test_user_id": "new-with-family",
                "create_family": True,
                "family_name": "Test Family",
            },
        )

        # Verify response
        assert response.status_code == 200

        # Verify family and membership were created
        assert mock_db_session.add.call_count == 3  # user + family + membership
        mock_db_session.flush.assert_called_once()


class TestTestCleanup:
    """Tests for DELETE /api/v1/auth/test-cleanup/{test_user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_test_cleanup_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should delete test user successfully."""
        mock_user = create_mock_user(apple_user_id="test_cleanup-user")

        # Mock user found
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute = AsyncMock(return_value=user_result)

        # Make request
        response = await client.delete("/api/v1/auth/test-cleanup/cleanup-user")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is True
        assert "Deleted test user" in data["message"]

        # Verify user was deleted
        mock_db_session.delete.assert_called_once_with(mock_user)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_cleanup_user_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
    ):
        """Should return deleted=False when user not found."""
        # Mock user not found
        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(return_value=user_result)

        # Make request
        response = await client.delete("/api/v1/auth/test-cleanup/nonexistent")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] is False
        assert "User not found" in data["message"]

        # Verify nothing was deleted
        mock_db_session.delete.assert_not_called()
