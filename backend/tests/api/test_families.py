"""
Comprehensive integration tests for family management endpoints.

Tests cover:
- POST /api/v1/families - Create family
- GET /api/v1/families/{id} - Get family details
- POST /api/v1/families/join - Join family with invite code
- PATCH /api/v1/families/{id}/members/{user_id}/role - Update member role
- DELETE /api/v1/families/{id}/members/{user_id} - Remove member
- POST /api/v1/families/{id}/leave - Leave family
- DELETE /api/v1/families/{id} - Delete family (via leave endpoint)
- POST /api/v1/families/{id}/regenerate-code - Regenerate invite code
- PATCH /api/v1/families/{id} - Update family name

Test scenarios:
- Happy path (200, 201 responses)
- Validation errors (400, 422)
- Not found (404)
- Unauthorized (401)
- Forbidden (403)
- Rate limiting (429)
- Brute force protection
- Cache invalidation
- Push notifications
"""
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    TEST_ADMIN_USER_ID,
    create_mock_membership,
    create_mock_family,
    create_mock_user,
)


# ============== Helper Functions ==============

def create_mock_family_with_members(
    family_id: str = TEST_FAMILY_ID,
    name: str = "Test Family",
    invite_code: str = "ABC12345",
    members: list = None,
) -> MagicMock:
    """Create a mock Family object with members."""
    family = create_mock_family(family_id=family_id, name=name, invite_code=invite_code)
    family.members = members or []
    return family


# ============== Create Family Tests ==============

class TestCreateFamily:
    """Tests for POST /api/v1/families endpoint."""

    @pytest.mark.asyncio
    async def test_create_family_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should successfully create a new family with user as admin."""
        # Mock flush to assign family ID
        async def mock_flush():
            pass

        mock_db_session.flush = mock_flush

        # Mock refresh to populate created family
        async def mock_refresh(obj):
            obj.id = UUID(TEST_FAMILY_ID)
            obj.invite_code = "ABC12345"
            obj.created_at = datetime.now(UTC)

        mock_db_session.refresh = mock_refresh

        # Make request
        response = await client.post(
            "/api/v1/families",
            json={"name": "My New Family"},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My New Family"
        assert "invite_code" in data
        assert data["role"] == "admin"
        assert "id" in data

        # Verify database calls
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_family_validation_error_missing_name(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for missing family name."""
        response = await client.post(
            "/api/v1/families",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_family_unauthorized_no_token(
        self,
        client: AsyncClient,
    ):
        """Should return 401 without auth token."""
        response = await client.post(
            "/api/v1/families",
            json={"name": "Test Family"},
        )

        assert response.status_code == 401


# ============== Get Family Details Tests ==============

class TestGetFamily:
    """Tests for GET /api/v1/families/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_family_success_with_cache(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return family details from cache if available."""
        # Mock membership check
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(side_effect=[membership_result])

        # Create mock Pydantic response object
        from app.api.endpoints.families import FamilyDetailResponse, FamilyMemberResponse

        cached_response = FamilyDetailResponse(
            id=test_family_id,
            name="Test Family",
            invite_code="ABC12345",
            created_at=datetime.now(UTC),
            members=[
                FamilyMemberResponse(
                    id=str(uuid4()),
                    user_id=test_user_id,
                    email="test@example.com",
                    first_name="Test",
                    last_name="User",
                    role="admin",
                    joined_at=datetime.now(UTC),
                )
            ],
        )

        with patch("app.api.endpoints.families.cache_get") as mock_cache_get:
            mock_cache_get.return_value = cached_response

            response = await client.get(
                f"/api/v1/families/{test_family_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        # Cache was checked
        mock_cache_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_family_success_from_database(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should fetch family from database and cache it."""
        # Mock membership check
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock family query with members
        mock_user = create_mock_user(
            user_id=test_user_id,
            email="test@example.com",
            first_name="Test",
        )

        mock_member = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_member.user = mock_user

        mock_family = create_mock_family_with_members(
            family_id=test_family_id,
            members=[mock_member],
        )

        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        with patch("app.api.endpoints.families.cache_get", return_value=None), \
             patch("app.api.endpoints.families.cache_set") as mock_cache_set:

            response = await client.get(
                f"/api/v1/families/{test_family_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_family_id
        assert data["name"] == "Test Family"
        assert data["invite_code"] == "ABC12345"
        assert len(data["members"]) == 1
        assert data["members"][0]["user_id"] == test_user_id

        # Verify cache was set
        mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_family_forbidden_not_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 403 if user is not a family member."""
        # Mock no membership found
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[membership_result])

        response = await client.get(
            f"/api/v1/families/{test_family_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_family_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 if family doesn't exist."""
        # Mock membership exists
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock family not found
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        with patch("app.api.endpoints.families.cache_get", return_value=None):
            response = await client.get(
                f"/api/v1/families/{test_family_id}",
                headers=auth_headers,
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_family_unauthorized_no_token(
        self,
        client: AsyncClient,
        test_family_id: str,
    ):
        """Should return 401 without auth token."""
        response = await client.get(f"/api/v1/families/{test_family_id}")
        assert response.status_code == 401


# ============== Join Family Tests ==============

class TestJoinFamily:
    """Tests for POST /api/v1/families/join endpoint."""

    @pytest.mark.asyncio
    async def test_join_family_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully join a family with valid invite code."""
        # Mock lockout check - user not locked
        user_result1 = MagicMock()
        user_result1.scalar_one_or_none.return_value = None

        # Mock backoff check - no failed attempts
        user_result2 = MagicMock()
        user_result2.scalar_one_or_none.return_value = None

        # Mock rate limit check - count queries
        count_result1 = MagicMock()
        count_result1.scalar.return_value = 0  # User attempts
        count_result2 = MagicMock()
        count_result2.scalar.return_value = 0  # IP attempts

        # Mock family lookup
        mock_family = create_mock_family(family_id=test_family_id)
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        # Mock existing membership check - not a member
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        # Mock user lookup for handle_successful_invite_attempt
        mock_user_for_reset = create_mock_user(user_id=test_user_id)
        mock_user_for_reset.failed_invite_attempts = 0
        user_result3 = MagicMock()
        user_result3.scalar_one_or_none.return_value = mock_user_for_reset

        # Mock user lookup for notification
        mock_user = create_mock_user(user_id=test_user_id, first_name="John")
        user_result4 = MagicMock()
        user_result4.scalar_one_or_none.return_value = mock_user

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result1,  # lockout check
                user_result2,  # backoff check
                count_result1,  # user rate limit
                count_result2,  # IP rate limit
                family_result,  # family lookup
                existing_result,  # existing membership check
                user_result3,  # user lookup for handle_successful_invite_attempt
                user_result4,  # user lookup for notification
            ]
        )

        # Mock async commit and log_invite_attempt
        mock_db_session.commit = AsyncMock()

        async def mock_get_tokens(*args, **kwargs):
            return []

        with patch("app.api.endpoints.families.cache_delete") as mock_cache_delete, \
             patch("app.api.endpoints.families.get_filtered_family_member_tokens", side_effect=mock_get_tokens), \
             patch("app.api.endpoints.families.apns_service"):

            response = await client.post(
                "/api/v1/families/join",
                json={"invite_code": "ABC12345"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["family"]["id"] == test_family_id
        assert data["family"]["name"] == "Test Family"
        assert data["family"]["role"] == "member"
        assert "Successfully joined" in data["message"]

        # Verify membership was created
        mock_db_session.add.assert_called()

        # Verify cache was invalidated
        mock_cache_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_join_family_invalid_code(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 404 for invalid invite code."""
        # Mock security checks passing
        user_result1 = MagicMock()
        user_result1.scalar_one_or_none.return_value = None
        user_result2 = MagicMock()
        user_result2.scalar_one_or_none.return_value = None
        count_result1 = MagicMock()
        count_result1.scalar.return_value = 0
        count_result2 = MagicMock()
        count_result2.scalar.return_value = 0

        # Mock family not found
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = None

        # Mock user query for handle_failed_invite_attempt
        mock_user = create_mock_user(user_id=test_user_id)
        mock_user.failed_invite_attempts = 0
        user_result3 = MagicMock()
        user_result3.scalar_one_or_none.return_value = mock_user

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result1,
                user_result2,
                count_result1,
                count_result2,
                family_result,
                user_result3,  # handle_failed_invite_attempt user query
            ]
        )

        mock_db_session.commit = AsyncMock()

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "INVALID1"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "Invalid invite code" in response.json()["detail"]

        # Verify failed attempt was logged
        assert mock_db_session.commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_join_family_already_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 if user is already a member."""
        # Mock security checks
        user_result1 = MagicMock()
        user_result1.scalar_one_or_none.return_value = None
        user_result2 = MagicMock()
        user_result2.scalar_one_or_none.return_value = None
        count_result1 = MagicMock()
        count_result1.scalar.return_value = 0
        count_result2 = MagicMock()
        count_result2.scalar.return_value = 0

        # Mock family found
        mock_family = create_mock_family(family_id=test_family_id)
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        # Mock existing membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result1,
                user_result2,
                count_result1,
                count_result2,
                family_result,
                existing_result,
            ]
        )

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "ABC12345"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "already a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_join_family_rate_limited_by_user(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 429 when user exceeds rate limit."""
        # Mock lockout and backoff checks
        user_result1 = MagicMock()
        user_result1.scalar_one_or_none.return_value = None
        user_result2 = MagicMock()
        user_result2.scalar_one_or_none.return_value = None

        # Mock rate limit exceeded
        count_result = MagicMock()
        count_result.scalar.return_value = 6  # Over limit of 5

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result1, user_result2, count_result]
        )

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "TEST1234"},
            headers=auth_headers,
        )

        assert response.status_code == 429
        assert "Too many" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_join_family_locked_out(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 when user account is locked out."""
        # Mock locked out user
        mock_user = create_mock_user(user_id=test_user_id)
        mock_user.is_locked_out = True
        mock_user.lockout_expires_at = datetime.now(UTC) + timedelta(minutes=30)

        user_result = MagicMock()
        user_result.scalar_one_or_none.return_value = mock_user

        mock_db_session.execute = AsyncMock(side_effect=[user_result])

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "TEST1234"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "locked" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_join_family_exponential_backoff(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 429 during exponential backoff period."""
        # Mock lockout check - not locked
        user_result1 = MagicMock()
        user_result1.scalar_one_or_none.return_value = None

        # Mock user with failed attempts
        mock_user = create_mock_user(user_id=test_user_id)
        mock_user.failed_invite_attempts = 3
        mock_user.last_failed_invite_at = datetime.now(UTC) - timedelta(seconds=30)

        user_result2 = MagicMock()
        user_result2.scalar_one_or_none.return_value = mock_user

        mock_db_session.execute = AsyncMock(
            side_effect=[user_result1, user_result2]
        )

        response = await client.post(
            "/api/v1/families/join",
            json={"invite_code": "TEST1234"},
            headers=auth_headers,
        )

        assert response.status_code == 429
        assert "wait" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_join_family_sends_notification(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should send push notification to family members."""
        # Setup all mocks for successful join
        user_result1 = MagicMock()
        user_result1.scalar_one_or_none.return_value = None
        user_result2 = MagicMock()
        user_result2.scalar_one_or_none.return_value = None
        count_result1 = MagicMock()
        count_result1.scalar.return_value = 0
        count_result2 = MagicMock()
        count_result2.scalar.return_value = 0

        mock_family = create_mock_family(family_id=test_family_id)
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        # Mock user for handle_successful_invite_attempt
        mock_user_for_reset = create_mock_user(user_id=test_user_id)
        mock_user_for_reset.failed_invite_attempts = 0
        user_result3 = MagicMock()
        user_result3.scalar_one_or_none.return_value = mock_user_for_reset

        # Mock user for notification
        mock_user = create_mock_user(user_id=test_user_id, first_name="Alice")
        user_result4 = MagicMock()
        user_result4.scalar_one_or_none.return_value = mock_user

        mock_db_session.execute = AsyncMock(
            side_effect=[
                user_result1, user_result2, count_result1, count_result2,
                family_result, existing_result, user_result3, user_result4,
            ]
        )

        mock_db_session.commit = AsyncMock()

        async def mock_get_tokens(*args, **kwargs):
            return ["token1", "token2"]

        mock_send_to_multiple = AsyncMock()

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.get_filtered_family_member_tokens", side_effect=mock_get_tokens) as mock_get_tokens_patch, \
             patch("app.api.endpoints.families.apns_service") as mock_apns:

            mock_apns.send_to_multiple = mock_send_to_multiple

            response = await client.post(
                "/api/v1/families/join",
                json={"invite_code": "ABC12345"},
                headers=auth_headers,
            )

        assert response.status_code == 200

        # Verify notification was sent
        mock_get_tokens_patch.assert_called_once()
        mock_send_to_multiple.assert_called_once()

        # Verify notification content
        call_args = mock_send_to_multiple.call_args
        assert call_args[1]["device_tokens"] == ["token1", "token2"]
        assert "Alice" in call_args[1]["title"]
        assert call_args[1]["data"]["type"] == "member_joined"


# ============== Update Member Role Tests ==============

class TestUpdateMemberRole:
    """Tests for PATCH /api/v1/families/{id}/members/{user_id}/role endpoint."""

    @pytest.mark.asyncio
    async def test_update_member_role_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should successfully update member role from member to admin."""
        # Mock admin's membership
        mock_admin_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        # Mock target member's membership
        mock_target_user = create_mock_user(
            user_id=test_admin_user_id,
            first_name="Bob",
        )
        mock_target_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_target_membership.user = mock_target_user

        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = mock_target_membership

        # Mock family query for notification
        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result, family_result]
        )

        mock_db_session.commit = AsyncMock()

        # Mock refresh
        async def mock_refresh(obj):
            obj.role = "admin"

        mock_db_session.refresh = mock_refresh

        async def mock_get_tokens(*args):
            return []

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.get_user_device_tokens", side_effect=mock_get_tokens), \
             patch("app.api.endpoints.families.apns_service"):

            response = await client.patch(
                f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}/role",
                json={"role": "admin"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert data["user_id"] == test_admin_user_id

        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_member_role_forbidden_not_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should return 403 if user is not an admin."""
        # Mock non-admin membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(side_effect=[result])

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}/role",
            json={"role": "admin"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "Only family admins" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_member_role_cannot_demote_last_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when trying to demote the last admin."""
        # Mock admin's membership
        mock_admin_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        # Mock target (another admin)
        mock_target_user = create_mock_user(user_id=test_admin_user_id)
        mock_target_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_target_membership.user = mock_target_user

        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = mock_target_membership

        # Mock admin count = 1 (only one admin)
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result, count_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}/role",
            json={"role": "member"},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "last admin" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_member_role_member_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 if member not found."""
        # Mock admin's membership
        mock_admin_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        # Mock target not found
        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}/role",
            json={"role": "admin"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_member_role_validation_error_invalid_role(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should return 422 for invalid role value."""
        response = await client.patch(
            f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}/role",
            json={"role": "superuser"},  # Invalid role
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_member_role_sends_notification(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should send notification to member when role changes."""
        # Setup mocks
        mock_admin_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        mock_target_user = create_mock_user(user_id=test_admin_user_id)
        mock_target_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_target_membership.user = mock_target_user

        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = mock_target_membership

        # Mock family for notification
        mock_family = create_mock_family(family_id=test_family_id, name="Smith Family")
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result, family_result]
        )

        mock_db_session.commit = AsyncMock()

        async def mock_refresh(obj):
            obj.role = "admin"

        mock_db_session.refresh = mock_refresh

        async def mock_get_tokens(*args):
            return ["device_token"]

        mock_send_to_multiple = AsyncMock()

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.get_user_device_tokens", side_effect=mock_get_tokens) as mock_get_tokens_patch, \
             patch("app.api.endpoints.families.apns_service") as mock_apns:

            mock_apns.send_to_multiple = mock_send_to_multiple

            response = await client.patch(
                f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}/role",
                json={"role": "admin"},
                headers=auth_headers,
            )

        assert response.status_code == 200

        # Verify notification sent
        mock_get_tokens_patch.assert_called_once()
        mock_send_to_multiple.assert_called_once()

        call_args = mock_send_to_multiple.call_args
        assert "admin" in call_args[1]["body"]


# ============== Remove Family Member Tests ==============

class TestRemoveFamilyMember:
    """Tests for DELETE /api/v1/families/{id}/members/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_member_success_admin_removes_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should allow admin to remove a member."""
        # Mock admin's membership
        mock_admin_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        # Mock target membership
        mock_target_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="member",
        )
        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = mock_target_membership

        # Mock family for notification
        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result, family_result]
        )

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.get_user_device_tokens", return_value=[]), \
             patch("app.api.endpoints.families.apns_service"):

            response = await client.delete(
                f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert "removed successfully" in response.json()["message"]

        # Verify member was deleted
        mock_db_session.delete.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_member_success_self_removal(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should allow member to remove themselves."""
        # Mock user's membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock family
        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, membership_result, family_result]
        )

        with patch("app.api.endpoints.families.cache_delete"):
            response = await client.delete(
                f"/api/v1/families/{test_family_id}/members/{test_user_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200
        mock_db_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_member_forbidden_member_removing_other(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should return 403 when non-admin tries to remove another member."""
        # Mock non-admin membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        result = MagicMock()
        result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(side_effect=[result])

        response = await client.delete(
            f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "only remove yourself" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_member_cannot_remove_last_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 when trying to remove the last admin."""
        # Mock admin membership
        mock_admin_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        # Mock admin count = 1
        count_result = MagicMock()
        count_result.scalar.return_value = 1

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, admin_result, count_result]
        )

        response = await client.delete(
            f"/api/v1/families/{test_family_id}/members/{test_user_id}",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "last admin" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_member_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 if member not found in family."""
        # Mock admin membership
        mock_admin_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        # Mock target not found
        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result]
        )

        response = await client.delete(
            f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_remove_member_sends_notification_to_removed_user(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should send notification to removed user."""
        # Setup mocks
        mock_admin_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        admin_result = MagicMock()
        admin_result.scalar_one_or_none.return_value = mock_admin_membership

        mock_target_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="member",
        )
        target_result = MagicMock()
        target_result.scalar_one_or_none.return_value = mock_target_membership

        mock_family = create_mock_family(name="Smith Family")
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[admin_result, target_result, family_result]
        )

        mock_db_session.commit = AsyncMock()

        async def mock_get_tokens(*args):
            return ["token"]

        mock_send_to_multiple = AsyncMock()

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.get_user_device_tokens", side_effect=mock_get_tokens) as mock_get_tokens_patch, \
             patch("app.api.endpoints.families.apns_service") as mock_apns:

            mock_apns.send_to_multiple = mock_send_to_multiple

            response = await client.delete(
                f"/api/v1/families/{test_family_id}/members/{test_admin_user_id}",
                headers=auth_headers,
            )

        assert response.status_code == 200

        # Verify notification sent
        mock_get_tokens_patch.assert_called_once()
        mock_send_to_multiple.assert_called_once()

        call_args = mock_send_to_multiple.call_args
        assert "removed" in call_args[1]["title"]


# ============== Leave Family Tests ==============

class TestLeaveFamily:
    """Tests for POST /api/v1/families/{id}/leave endpoint."""

    @pytest.mark.asyncio
    async def test_leave_family_member_leaves(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should allow member to leave family."""
        # Mock member's membership
        mock_user = create_mock_user(user_id=test_user_id, first_name="Alice")
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_membership.user = mock_user

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock family
        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        # Mock counts (other admins exist)
        other_admins_result = MagicMock()
        other_admins_result.scalar.return_value = 1
        other_members_result = MagicMock()
        other_members_result.scalar.return_value = 1

        mock_db_session.execute = AsyncMock(
            side_effect=[
                membership_result,
                family_result,
                other_admins_result,
                other_members_result,
            ]
        )

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.get_admin_device_tokens", return_value=[]), \
             patch("app.api.endpoints.families.apns_service"):

            response = await client.post(
                f"/api/v1/families/{test_family_id}/leave",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["action"] == "left"
        assert data["family_name"] == "Test Family"

        mock_db_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_leave_family_admin_leaves_with_other_admins(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should allow admin to leave when other admins exist."""
        # Mock admin's membership
        mock_user = create_mock_user(user_id=test_user_id, first_name="Bob")
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.user = mock_user

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        # Other admins exist
        other_admins_result = MagicMock()
        other_admins_result.scalar.return_value = 2  # Other admins exist

        # Need other_members_result query too - not just other_admins
        # The endpoint checks both counts, not just other_admins
        other_members_result = MagicMock()
        other_members_result.scalar.return_value = 3  # Total other members

        mock_db_session.execute = AsyncMock(
            side_effect=[
                membership_result,
                family_result,
                other_admins_result,
                other_members_result,  # Added this missing result
            ]
        )

        mock_db_session.commit = AsyncMock()

        async def mock_get_tokens(*args, **kwargs):
            return []

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.get_admin_device_tokens", side_effect=mock_get_tokens), \
             patch("app.api.endpoints.families.apns_service"):

            response = await client.post(
                f"/api/v1/families/{test_family_id}/leave",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "left"

    @pytest.mark.asyncio
    async def test_leave_family_only_admin_no_members_deletes_family(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should delete family when only admin with no other members leaves."""
        # Mock admin's membership
        mock_user = create_mock_user(user_id=test_user_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.user = mock_user

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        # No other admins or members
        other_admins_result = MagicMock()
        other_admins_result.scalar.return_value = 0
        other_members_result = MagicMock()
        other_members_result.scalar.return_value = 0

        mock_db_session.execute = AsyncMock(
            side_effect=[
                membership_result,
                family_result,
                other_admins_result,
                other_members_result,
            ]
        )

        with patch("app.api.endpoints.families.cache_delete"):
            response = await client.post(
                f"/api/v1/families/{test_family_id}/leave",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "family_deleted"

        # Verify family was deleted (not just membership)
        mock_db_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_leave_family_only_admin_with_members_requires_new_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 if only admin tries to leave without promoting someone."""
        # Mock admin's membership
        mock_user = create_mock_user(user_id=test_user_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.user = mock_user

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        # No other admins, but members exist
        other_admins_result = MagicMock()
        other_admins_result.scalar.return_value = 0
        other_members_result = MagicMock()
        other_members_result.scalar.return_value = 2  # Other members exist

        mock_db_session.execute = AsyncMock(
            side_effect=[
                membership_result,
                family_result,
                other_admins_result,
                other_members_result,
            ]
        )

        response = await client.post(
            f"/api/v1/families/{test_family_id}/leave",
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "only admin" in response.json()["detail"]
        assert "select a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_leave_family_only_admin_promotes_new_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_admin_user_id: str,
        test_family_id: str,
    ):
        """Should promote new admin when only admin leaves."""
        # Mock admin's membership
        mock_user = create_mock_user(user_id=test_user_id, first_name="Alice")
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.user = mock_user

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        # No other admins, members exist
        other_admins_result = MagicMock()
        other_admins_result.scalar.return_value = 0
        other_members_result = MagicMock()
        other_members_result.scalar.return_value = 1

        # Mock new admin membership
        mock_new_admin_user = create_mock_user(user_id=test_admin_user_id)
        mock_new_admin_membership = create_mock_membership(
            user_id=test_admin_user_id,
            family_id=test_family_id,
            role="member",
        )
        mock_new_admin_membership.user = mock_new_admin_user

        new_admin_result = MagicMock()
        new_admin_result.scalar_one_or_none.return_value = mock_new_admin_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[
                membership_result,
                family_result,
                other_admins_result,
                other_members_result,
                new_admin_result,
            ]
        )

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.get_user_device_tokens", return_value=[]), \
             patch("app.api.endpoints.families.apns_service"):

            response = await client.post(
                f"/api/v1/families/{test_family_id}/leave",
                json={"new_admin_user_id": test_admin_user_id},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "left_promoted"

        # Verify new admin was promoted and old admin removed
        mock_db_session.flush.assert_called_once()
        mock_db_session.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_leave_family_cannot_promote_self(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 400 if trying to promote self as new admin."""
        # Mock admin's membership
        mock_user = create_mock_user(user_id=test_user_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        mock_membership.user = mock_user

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        other_admins_result = MagicMock()
        other_admins_result.scalar.return_value = 0
        other_members_result = MagicMock()
        other_members_result.scalar.return_value = 1

        # Mock new admin lookup (same user)
        new_admin_result = MagicMock()
        new_admin_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(
            side_effect=[
                membership_result,
                family_result,
                other_admins_result,
                other_members_result,
                new_admin_result,
            ]
        )

        response = await client.post(
            f"/api/v1/families/{test_family_id}/leave",
            json={"new_admin_user_id": test_user_id},
            headers=auth_headers,
        )

        assert response.status_code == 400
        assert "cannot select yourself" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_leave_family_forbidden_not_member(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_family_id: str,
    ):
        """Should return 403 if user is not a family member."""
        # Mock no membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[membership_result])

        response = await client.post(
            f"/api/v1/families/{test_family_id}/leave",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_leave_family_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 if family doesn't exist."""
        # Mock membership exists
        mock_user = create_mock_user(user_id=test_user_id)
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
        )
        mock_membership.user = mock_user

        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock family not found
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        response = await client.post(
            f"/api/v1/families/{test_family_id}/leave",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]


# ============== Regenerate Invite Code Tests ==============

class TestRegenerateInviteCode:
    """Tests for POST /api/v1/families/{id}/regenerate-code endpoint."""

    @pytest.mark.asyncio
    async def test_regenerate_code_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully regenerate invite code."""
        # Mock admin membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock family
        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        # Mock refresh to update invite code
        async def mock_refresh(obj):
            obj.invite_code = "NEW12345"

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.families.cache_delete"), \
             patch("app.api.endpoints.families.generate_invite_code", return_value="NEW12345"):

            response = await client.post(
                f"/api/v1/families/{test_family_id}/regenerate-code",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["invite_code"] == "NEW12345"
        assert data["role"] == "admin"

        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_regenerate_code_forbidden_not_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 403 if user is not an admin."""
        # Mock non-admin membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(side_effect=[membership_result])

        response = await client.post(
            f"/api/v1/families/{test_family_id}/regenerate-code",
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "Only family admins" in response.json()["detail"]


# ============== Update Family Tests ==============

class TestUpdateFamily:
    """Tests for PATCH /api/v1/families/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_family_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should successfully update family name."""
        # Mock admin membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock family
        mock_family = create_mock_family()
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = mock_family

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        # Mock refresh
        async def mock_refresh(obj):
            obj.name = "Updated Family Name"

        mock_db_session.refresh = mock_refresh

        with patch("app.api.endpoints.families.cache_delete"):
            response = await client.patch(
                f"/api/v1/families/{test_family_id}",
                json={"name": "Updated Family Name"},
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Family Name"

        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_family_forbidden_not_admin(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 403 if user is not an admin."""
        # Mock non-admin membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="member",
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(side_effect=[membership_result])

        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 403
        assert "Only family admins" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_family_invalid_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid family ID format."""
        response = await client.patch(
            "/api/v1/families/invalid-uuid",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_family_not_found(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return 404 if family doesn't exist."""
        # Mock admin membership
        mock_membership = create_mock_membership(
            user_id=test_user_id,
            family_id=test_family_id,
            role="admin",
        )
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        # Mock family not found
        family_result = MagicMock()
        family_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(
            side_effect=[membership_result, family_result]
        )

        response = await client.patch(
            f"/api/v1/families/{test_family_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
