"""
Comprehensive unit tests for notification services.

Tests cover:
- FamilyNotificationService methods (get_other_family_member_tokens, get_all_family_member_tokens, get_filtered_family_member_tokens)
- APNsService methods (send_notification, send_to_multiple, token generation, configuration)
- Notification filtering logic based on user preferences
- Error handling (APNs failures, expired tokens, configuration issues)
- Edge cases (no family members, all notifications disabled, missing preferences)

All external dependencies (APNS HTTP calls, database) are mocked for isolated unit testing.
"""
import base64
import time
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
import httpx
import jwt

from app.services.family_notifications import (
    get_other_family_member_tokens,
    get_all_family_member_tokens,
    get_filtered_family_member_tokens,
    NOTIFICATION_TYPE_TO_PREF,
)
from app.services.apns import APNsService


# ============== Test Data ==============

TEST_USER_ID_1 = uuid4()
TEST_USER_ID_2 = uuid4()
TEST_USER_ID_3 = uuid4()
TEST_FAMILY_ID = uuid4()
TEST_DEVICE_TOKEN_1 = "a" * 64
TEST_DEVICE_TOKEN_2 = "b" * 64
TEST_DEVICE_TOKEN_3 = "c" * 64


# ============== Mock Helpers ==============

def create_mock_family_member(user_id: UUID, family_id: UUID = TEST_FAMILY_ID, role: str = "member") -> MagicMock:
    """Create a mock FamilyMember object."""
    member = MagicMock()
    member.user_id = user_id
    member.family_id = family_id
    member.role = role
    member.joined_at = datetime.now(UTC)
    return member


def create_mock_device_token(user_id: UUID, device_token: str, is_active: bool = True) -> MagicMock:
    """Create a mock UserDeviceToken object."""
    token = MagicMock()
    token.id = uuid4()
    token.user_id = user_id
    token.device_token = device_token
    token.is_active = is_active
    token.created_at = datetime.now(UTC)
    return token


def create_mock_notification_preference(
    user_id: UUID,
    family_member_joined: bool = True,
    pet_added: bool = True,
    medication_created: bool = True,
    **kwargs
) -> MagicMock:
    """Create a mock NotificationPreference object."""
    pref = MagicMock()
    pref.id = uuid4()
    pref.user_id = user_id
    pref.family_member_joined = family_member_joined
    pref.family_role_changed = kwargs.get("family_role_changed", True)
    pref.family_member_left = kwargs.get("family_member_left", True)
    pref.family_member_left_promoted = kwargs.get("family_member_left_promoted", True)
    pref.family_account_deleted = kwargs.get("family_account_deleted", True)
    pref.family_account_deleted_promoted = kwargs.get("family_account_deleted_promoted", True)
    pref.pet_added = pet_added
    pref.pet_updated = kwargs.get("pet_updated", True)
    pref.pet_deleted = kwargs.get("pet_deleted", True)
    pref.medication_created = medication_created
    pref.medication_updated = kwargs.get("medication_updated", True)
    pref.medication_archived = kwargs.get("medication_archived", True)
    return pref


def create_mock_db_result(values: list) -> MagicMock:
    """Create a mock database result that returns scalars."""
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=values)
    result.scalars = MagicMock(return_value=scalars_mock)
    return result


# ============== FamilyNotificationService Tests ==============

class TestGetOtherFamilyMemberTokens:
    """Test get_other_family_member_tokens function."""

    @pytest.mark.asyncio
    async def test_returns_tokens_excluding_specified_user(self):
        """Should return device tokens for all family members except the excluded user."""
        # Setup
        db = AsyncMock()

        # Mock family members query - returns 2 other members
        members_result = create_mock_db_result([TEST_USER_ID_2, TEST_USER_ID_3])

        # Mock device tokens query - returns their tokens
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_2, TEST_DEVICE_TOKEN_3])

        db.execute = AsyncMock(side_effect=[members_result, tokens_result])

        # Execute
        tokens = await get_other_family_member_tokens(db, TEST_FAMILY_ID, TEST_USER_ID_1)

        # Assert
        assert tokens == [TEST_DEVICE_TOKEN_2, TEST_DEVICE_TOKEN_3]
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_other_members(self):
        """Should return empty list when only the excluded user is in the family."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([])  # No other members
        db.execute = AsyncMock(return_value=members_result)

        # Execute
        tokens = await get_other_family_member_tokens(db, TEST_FAMILY_ID, TEST_USER_ID_1)

        # Assert
        assert tokens == []
        assert db.execute.call_count == 1  # Should not query for tokens

    @pytest.mark.asyncio
    async def test_only_returns_active_tokens(self):
        """Should only return tokens where is_active=True."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_2])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_2])  # Only active token
        db.execute = AsyncMock(side_effect=[members_result, tokens_result])

        # Execute
        tokens = await get_other_family_member_tokens(db, TEST_FAMILY_ID, TEST_USER_ID_1)

        # Assert
        assert tokens == [TEST_DEVICE_TOKEN_2]

    @pytest.mark.asyncio
    async def test_handles_multiple_tokens_per_user(self):
        """Should return all active tokens when a user has multiple devices."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_2])

        # User 2 has 2 devices
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_2, TEST_DEVICE_TOKEN_3])
        db.execute = AsyncMock(side_effect=[members_result, tokens_result])

        # Execute
        tokens = await get_other_family_member_tokens(db, TEST_FAMILY_ID, TEST_USER_ID_1)

        # Assert
        assert len(tokens) == 2
        assert TEST_DEVICE_TOKEN_2 in tokens
        assert TEST_DEVICE_TOKEN_3 in tokens


class TestGetAllFamilyMemberTokens:
    """Test get_all_family_member_tokens function."""

    @pytest.mark.asyncio
    async def test_returns_all_family_member_tokens(self):
        """Should return device tokens for all family members including current user."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_1, TEST_USER_ID_2, TEST_USER_ID_3])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1, TEST_DEVICE_TOKEN_2, TEST_DEVICE_TOKEN_3])
        db.execute = AsyncMock(side_effect=[members_result, tokens_result])

        # Execute
        tokens = await get_all_family_member_tokens(db, TEST_FAMILY_ID)

        # Assert
        assert len(tokens) == 3
        assert TEST_DEVICE_TOKEN_1 in tokens

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_family_has_no_members(self):
        """Should return empty list for a family with no members."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([])
        db.execute = AsyncMock(return_value=members_result)

        # Execute
        tokens = await get_all_family_member_tokens(db, TEST_FAMILY_ID)

        # Assert
        assert tokens == []

    @pytest.mark.asyncio
    async def test_only_returns_active_tokens(self):
        """Should filter out inactive device tokens."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_1, TEST_USER_ID_2])
        # Only 1 active token returned (inactive ones filtered by query)
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1])
        db.execute = AsyncMock(side_effect=[members_result, tokens_result])

        # Execute
        tokens = await get_all_family_member_tokens(db, TEST_FAMILY_ID)

        # Assert
        assert tokens == [TEST_DEVICE_TOKEN_1]


class TestGetFilteredFamilyMemberTokens:
    """Test get_filtered_family_member_tokens function with notification preferences."""

    @pytest.mark.asyncio
    async def test_filters_by_notification_preference(self):
        """Should only return tokens for users who have the notification type enabled."""
        # Setup
        db = AsyncMock()

        # Three members in family (excluding trigger user)
        members_result = create_mock_db_result([TEST_USER_ID_2, TEST_USER_ID_3])

        # User 3 has this notification disabled
        prefs_result = create_mock_db_result([TEST_USER_ID_3])

        # Only User 2's token should be returned
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_2])

        db.execute = AsyncMock(side_effect=[members_result, prefs_result, tokens_result])

        # Execute
        tokens = await get_filtered_family_member_tokens(
            db, TEST_FAMILY_ID, TEST_USER_ID_1, "member_joined"
        )

        # Assert
        assert tokens == [TEST_DEVICE_TOKEN_2]
        assert db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_defaults_to_enabled_when_no_preference_row(self):
        """Should include users who don't have a preferences row (defaults to all enabled)."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_2, TEST_USER_ID_3])
        prefs_result = create_mock_db_result([])  # No one has disabled this notification
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_2, TEST_DEVICE_TOKEN_3])
        db.execute = AsyncMock(side_effect=[members_result, prefs_result, tokens_result])

        # Execute
        tokens = await get_filtered_family_member_tokens(
            db, TEST_FAMILY_ID, TEST_USER_ID_1, "pet_added"
        )

        # Assert
        assert len(tokens) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_disabled(self):
        """Should return empty list when all users have disabled the notification."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_2, TEST_USER_ID_3])
        # Both users have it disabled
        prefs_result = create_mock_db_result([TEST_USER_ID_2, TEST_USER_ID_3])
        db.execute = AsyncMock(side_effect=[members_result, prefs_result])

        # Execute
        tokens = await get_filtered_family_member_tokens(
            db, TEST_FAMILY_ID, TEST_USER_ID_1, "medication_created"
        )

        # Assert
        assert tokens == []
        assert db.execute.call_count == 2  # Should not query tokens

    @pytest.mark.asyncio
    async def test_unknown_notification_type_fallback(self):
        """Should fall back to get_other_family_member_tokens for unknown notification types."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_2])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_2])
        db.execute = AsyncMock(side_effect=[members_result, tokens_result])

        # Execute - use unknown notification type
        tokens = await get_filtered_family_member_tokens(
            db, TEST_FAMILY_ID, TEST_USER_ID_1, "unknown_notification_type"
        )

        # Assert - should return all tokens without preference filtering
        assert tokens == [TEST_DEVICE_TOKEN_2]
        assert db.execute.call_count == 2  # No preference query

    @pytest.mark.asyncio
    async def test_all_notification_types_mapped(self):
        """Should have mappings for all expected notification types."""
        # Verify all expected types are in the mapping
        expected_types = [
            "member_joined",
            "role_changed",
            "member_left",
            "member_left_promoted",
            "account_deleted",
            "account_deleted_promoted",
            "pet_added",
            "pet_updated",
            "pet_deleted",
            "medication_created",
            "medication_updated",
            "medication_archived",
        ]

        for notification_type in expected_types:
            assert notification_type in NOTIFICATION_TYPE_TO_PREF
            pref_field = NOTIFICATION_TYPE_TO_PREF[notification_type]
            assert isinstance(pref_field, str)
            assert len(pref_field) > 0

    @pytest.mark.asyncio
    async def test_excludes_triggering_user(self):
        """Should not return tokens for the user who triggered the notification."""
        # Setup
        db = AsyncMock()
        # Only returns other users, not TEST_USER_ID_1
        members_result = create_mock_db_result([TEST_USER_ID_2])
        prefs_result = create_mock_db_result([])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_2])
        db.execute = AsyncMock(side_effect=[members_result, prefs_result, tokens_result])

        # Execute
        tokens = await get_filtered_family_member_tokens(
            db, TEST_FAMILY_ID, TEST_USER_ID_1, "pet_updated"
        )

        # Assert
        assert TEST_DEVICE_TOKEN_1 not in tokens


# ============== APNsService Tests ==============

class TestAPNsServiceConfiguration:
    """Test APNs service configuration and initialization."""

    def test_is_configured_returns_true_when_all_settings_present(self):
        """Should return True when all required APNs settings are configured."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64encodedkey==",
                apns_bundle_id="com.example.app",
                apns_use_sandbox=True,
            )
            service = APNsService()
            assert service.is_configured is True

    def test_is_configured_returns_false_when_settings_missing(self):
        """Should return False when any required setting is missing."""
        with patch("app.services.apns.get_settings") as mock_settings:
            # Missing apns_key_base64
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64=None,
                apns_bundle_id="com.example.app",
            )
            service = APNsService()
            assert service.is_configured is False

    def test_get_apns_url_uses_sandbox_when_configured(self):
        """Should use sandbox URL when apns_use_sandbox is True."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(apns_use_sandbox=True)
            service = APNsService()
            url = service._get_apns_url(TEST_DEVICE_TOKEN_1)
            assert "api.sandbox.push.apple.com" in url
            assert TEST_DEVICE_TOKEN_1 in url

    def test_get_apns_url_uses_production_when_not_sandbox(self):
        """Should use production URL when apns_use_sandbox is False."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(apns_use_sandbox=False)
            service = APNsService()
            url = service._get_apns_url(TEST_DEVICE_TOKEN_1)
            assert "api.push.apple.com" in url
            assert "sandbox" not in url


class TestAPNsTokenGeneration:
    """Test JWT token generation for APNs authentication."""

    def test_generates_valid_jwt_token(self):
        """Should generate a valid JWT token with correct claims."""
        with patch("app.services.apns.get_settings") as mock_settings:
            # Create a real ES256 private key for testing (using PyJWT's test key)
            private_key = b"""-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgevZzL1gdAFr88hb2
OF/2NxApJCzGCEDdfSp6VQO30hyhRANCAAQRWz+jn65BtOMvdyHKcvjBeBSDZH2r
1RTwjmYSi9R/zpBnuQ4EiMnCqfMPWiZqB4QdbAd0E7oH50VpuZ1P087G
-----END PRIVATE KEY-----"""

            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64=base64.b64encode(private_key).decode(),
                apns_bundle_id="com.example.app",
            )

            service = APNsService()
            token = service._generate_token()

            # Decode without verification to check structure
            decoded = jwt.decode(token, options={"verify_signature": False})

            assert decoded["iss"] == "TEAM123"
            assert "iat" in decoded
            assert isinstance(token, str)

    def test_caches_token_for_one_hour(self):
        """Should cache the generated token and reuse it within the hour."""
        with patch("app.services.apns.get_settings") as mock_settings:
            private_key = b"test-key"
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64=base64.b64encode(private_key).decode(),
            )

            service = APNsService()

            with patch("app.services.apns.jwt.encode", return_value="mock-token") as mock_encode:
                token1 = service._generate_token()
                token2 = service._generate_token()

                # Should only call encode once (second call uses cache)
                assert token1 == token2
                assert mock_encode.call_count == 1

    def test_regenerates_token_when_expired(self):
        """Should regenerate token when cached token is expired."""
        with patch("app.services.apns.get_settings") as mock_settings:
            private_key = b"test-key"
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64=base64.b64encode(private_key).decode(),
            )

            service = APNsService()

            with patch("app.services.apns.time.time") as mock_time:
                with patch("app.services.apns.jwt.encode", return_value="mock-token") as mock_encode:
                    # First call at time 0
                    mock_time.return_value = 0
                    token1 = service._generate_token()

                    # Second call 2 hours later (token expired)
                    mock_time.return_value = 7200
                    token2 = service._generate_token()

                    # Should regenerate
                    assert mock_encode.call_count == 2

    def test_raises_error_when_key_not_configured(self):
        """Should raise ValueError when APNs key is not configured."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64=None,  # No key
            )

            service = APNsService()

            with pytest.raises(ValueError, match="APNs key not configured"):
                service._load_private_key()


class TestAPNsSendNotification:
    """Test sending individual push notifications."""

    @pytest.mark.asyncio
    async def test_sends_notification_successfully(self):
        """Should send notification and return True on success."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
                apns_use_sandbox=True,
            )

            service = APNsService()

            # Mock token generation to avoid base64 decoding
            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                # Mock the HTTP client
                with patch("app.services.apns.httpx.AsyncClient") as mock_client_class:
                    mock_response = MagicMock()
                    mock_response.status_code = 200

                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()

                    mock_client_class.return_value = mock_client

                    # Execute
                    result = await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title="Test Title",
                        body="Test Body"
                    )

                    # Assert
                    assert result is True
                    mock_client.post.assert_called_once()

                    # Verify payload structure
                    call_args = mock_client.post.call_args
                    payload = call_args.kwargs["json"]
                    assert payload["aps"]["alert"]["title"] == "Test Title"
                    assert payload["aps"]["alert"]["body"] == "Test Body"
                    assert payload["aps"]["sound"] == "default"

    @pytest.mark.asyncio
    async def test_includes_badge_when_provided(self):
        """Should include badge number in payload when provided."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                with patch("app.services.apns.httpx.AsyncClient") as mock_client_class:
                    mock_response = MagicMock(status_code=200)
                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    mock_client_class.return_value = mock_client

                    await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title="Test",
                        body="Test",
                        badge=5
                    )

                    call_args = mock_client.post.call_args
                    payload = call_args.kwargs["json"]
                    assert payload["aps"]["badge"] == 5

    @pytest.mark.asyncio
    async def test_includes_custom_data_when_provided(self):
        """Should include custom data payload when provided."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                with patch("app.services.apns.httpx.AsyncClient") as mock_client_class:
                    mock_response = MagicMock(status_code=200)
                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    mock_client_class.return_value = mock_client

                    custom_data = {"pet_id": "123", "action": "medication_reminder"}
                    await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title="Test",
                        body="Test",
                        data=custom_data
                    )

                    call_args = mock_client.post.call_args
                    payload = call_args.kwargs["json"]
                    assert payload["data"] == custom_data

    @pytest.mark.asyncio
    async def test_returns_false_when_not_configured(self):
        """Should return False and log warning when APNs is not configured."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id=None,  # Not configured
                apns_team_id=None,
                apns_key_base64=None,
            )

            service = APNsService()

            result = await service.send_notification(
                device_token=TEST_DEVICE_TOKEN_1,
                title="Test",
                body="Test"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_expired_device_token(self):
        """Should return False when device token is expired (410 status)."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                with patch("app.services.apns.httpx.AsyncClient") as mock_client_class:
                    mock_response = MagicMock()
                    mock_response.status_code = 410  # Token expired
                    mock_response.text = "Unregistered"

                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    mock_client_class.return_value = mock_client

                    result = await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title="Test",
                        body="Test"
                    )

                    assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_other_apns_errors(self):
        """Should return False on other APNs error status codes."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                with patch("app.services.apns.httpx.AsyncClient") as mock_client_class:
                    mock_response = MagicMock()
                    mock_response.status_code = 400  # Bad request
                    mock_response.text = "BadDeviceToken"

                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    mock_client_class.return_value = mock_client

                    result = await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title="Test",
                        body="Test"
                    )

                    assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_network_exception(self):
        """Should handle network exceptions and return False."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                # Mock the AsyncClient context manager to raise an exception
                mock_request = MagicMock()
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(side_effect=httpx.RequestError("Network error", request=mock_request))
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)

                with patch("app.services.apns.httpx.AsyncClient", return_value=mock_client):
                    result = await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title="Test",
                        body="Test"
                    )

                    assert result is False

    @pytest.mark.asyncio
    async def test_uses_http2_client(self):
        """Should use HTTP/2 for APNs requests."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                with patch("app.services.apns.httpx.AsyncClient") as mock_client_class:
                    mock_response = MagicMock(status_code=200)
                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    mock_client_class.return_value = mock_client

                    await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title="Test",
                        body="Test"
                    )

                    # Verify HTTP/2 was enabled
                    mock_client_class.assert_called_once()
                    call_kwargs = mock_client_class.call_args.kwargs
                    assert call_kwargs.get("http2") is True


class TestAPNsSendToMultiple:
    """Test sending notifications to multiple devices."""

    @pytest.mark.asyncio
    async def test_sends_to_all_devices(self):
        """Should send notification to all provided device tokens."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            # Mock successful sends
            with patch.object(service, "send_notification", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                tokens = [TEST_DEVICE_TOKEN_1, TEST_DEVICE_TOKEN_2, TEST_DEVICE_TOKEN_3]
                success_count = await service.send_to_multiple(
                    device_tokens=tokens,
                    title="Test Title",
                    body="Test Body"
                )

                assert success_count == 3
                assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_counts_only_successful_sends(self):
        """Should return count of only successful sends when some fail."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            # Mock some successes and some failures
            with patch.object(service, "send_notification", new_callable=AsyncMock) as mock_send:
                mock_send.side_effect = [True, False, True]  # 2 successes, 1 failure

                tokens = [TEST_DEVICE_TOKEN_1, TEST_DEVICE_TOKEN_2, TEST_DEVICE_TOKEN_3]
                success_count = await service.send_to_multiple(
                    device_tokens=tokens,
                    title="Test",
                    body="Test"
                )

                assert success_count == 2

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_token_list(self):
        """Should return 0 when given an empty list of tokens."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
            )

            service = APNsService()

            with patch.object(service, "send_notification", new_callable=AsyncMock) as mock_send:
                success_count = await service.send_to_multiple(
                    device_tokens=[],
                    title="Test",
                    body="Test"
                )

                assert success_count == 0
                mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_passes_custom_data_to_all_notifications(self):
        """Should include custom data in all notifications when provided."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
            )

            service = APNsService()
            custom_data = {"action": "family_update"}

            with patch.object(service, "send_notification", new_callable=AsyncMock) as mock_send:
                mock_send.return_value = True

                tokens = [TEST_DEVICE_TOKEN_1, TEST_DEVICE_TOKEN_2]
                await service.send_to_multiple(
                    device_tokens=tokens,
                    title="Test",
                    body="Test",
                    data=custom_data
                )

                # Verify custom data was passed to each call
                # The signature is: send_notification(device_token, title, body, data=None, badge=None)
                # So data is the 4th parameter (index 3 when counting args, or in kwargs)
                for call in mock_send.call_args_list:
                    # Check if data was passed as keyword argument
                    if "data" in call.kwargs:
                        assert call.kwargs["data"] == custom_data
                    # Or as positional argument (4th arg, index 3)
                    elif len(call.args) >= 4:
                        assert call.args[3] == custom_data
                    else:
                        # If neither, the test should fail
                        assert False, f"data argument not found in call: {call}"


# ============== Edge Cases and Integration Tests ==============

class TestNotificationFilteringEdgeCases:
    """Test edge cases in notification filtering logic."""

    @pytest.mark.asyncio
    async def test_handles_mixed_preferences(self):
        """Should correctly handle mix of users with and without preference rows."""
        # Setup
        db = AsyncMock()

        # 3 users total
        members_result = create_mock_db_result([TEST_USER_ID_2, TEST_USER_ID_3, uuid4()])

        # Only User 2 has a preference row, and it's disabled
        prefs_result = create_mock_db_result([TEST_USER_ID_2])

        # Should return tokens for User 3 and the user without preferences (default enabled)
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_2, TEST_DEVICE_TOKEN_3])

        db.execute = AsyncMock(side_effect=[members_result, prefs_result, tokens_result])

        # Execute
        tokens = await get_filtered_family_member_tokens(
            db, TEST_FAMILY_ID, TEST_USER_ID_1, "pet_updated"
        )

        # Assert - should return 2 tokens (excluding the one who disabled)
        assert len(tokens) == 2

    @pytest.mark.asyncio
    async def test_notification_type_to_pref_coverage(self):
        """Verify that all notification types map to valid preference fields."""
        # This test ensures the mapping is complete and correct
        from app.models.notification import NotificationPreference

        for notification_type, pref_field in NOTIFICATION_TYPE_TO_PREF.items():
            # Verify the field exists on the model
            assert hasattr(NotificationPreference, pref_field), \
                f"NotificationPreference missing field: {pref_field} for type: {notification_type}"


class TestAPNsEdgeCases:
    """Test edge cases in APNs service."""

    @pytest.mark.asyncio
    async def test_handles_extremely_long_notification_text(self):
        """Should handle very long notification text without errors."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                with patch("app.services.apns.httpx.AsyncClient") as mock_client_class:
                    mock_response = MagicMock(status_code=200)
                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    mock_client_class.return_value = mock_client

                    long_text = "A" * 1000
                    result = await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title=long_text,
                        body=long_text
                    )

                    assert result is True

    @pytest.mark.asyncio
    async def test_handles_special_characters_in_notifications(self):
        """Should properly encode special characters in notification text."""
        with patch("app.services.apns.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                apns_key_id="ABC123",
                apns_team_id="TEAM123",
                apns_key_base64="base64key==",
                apns_bundle_id="com.example.app",
            )

            service = APNsService()

            with patch.object(service, "_generate_token", return_value="mock-jwt-token"):
                with patch("app.services.apns.httpx.AsyncClient") as mock_client_class:
                    mock_response = MagicMock(status_code=200)
                    mock_client = AsyncMock()
                    mock_client.post = AsyncMock(return_value=mock_response)
                    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                    mock_client.__aexit__ = AsyncMock()
                    mock_client_class.return_value = mock_client

                    special_text = "Hello 👋 World! Test's \"quotes\" & <tags>"
                    result = await service.send_notification(
                        device_token=TEST_DEVICE_TOKEN_1,
                        title=special_text,
                        body=special_text
                    )

                    assert result is True

                    # Verify the text was passed correctly
                    call_args = mock_client.post.call_args
                    payload = call_args.kwargs["json"]
                    assert payload["aps"]["alert"]["title"] == special_text
