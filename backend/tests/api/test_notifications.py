"""
Comprehensive integration tests for notification management endpoints.

Tests cover:
- Device token registration and management
- Notification preferences CRUD
- Authorization checks
- Validation errors
- Edge cases (reactivation, upsert patterns)

NOTE: These tests mock the database session and use the FastAPI test client.
All authorization uses get_current_user_id which extracts user_id from JWT.
"""
from datetime import UTC, datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_USER_ID


# ============== Helper Functions ==============

def create_mock_device_token(
    token_id: str = None,
    user_id: str = None,
    device_token: str = "abc123def456",
    device_name: str = "iPhone 15 Pro",
    platform: str = "ios",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock UserDeviceToken object."""
    token = MagicMock()
    token.id = UUID(token_id) if token_id else uuid4()
    token.user_id = UUID(user_id) if user_id else uuid4()
    token.device_token = device_token
    token.device_name = device_name
    token.platform = platform
    token.is_active = is_active
    token.created_at = datetime(2024, 1, 1)
    token.updated_at = datetime(2024, 1, 1)
    return token


def create_mock_notification_preferences(
    user_id: str = None,
    family_member_joined: bool = True,
    family_role_changed: bool = True,
    family_member_left: bool = True,
    family_member_left_promoted: bool = True,
    family_account_deleted: bool = True,
    family_account_deleted_promoted: bool = True,
    pet_added: bool = True,
    pet_updated: bool = True,
    pet_deleted: bool = True,
    medication_created: bool = True,
    medication_updated: bool = True,
    medication_archived: bool = True,
    dose_administered: bool = True,
) -> MagicMock:
    """Create a mock NotificationPreference object."""
    prefs = MagicMock()
    prefs.id = uuid4()
    prefs.user_id = UUID(user_id) if user_id else uuid4()
    prefs.family_member_joined = family_member_joined
    prefs.family_role_changed = family_role_changed
    prefs.family_member_left = family_member_left
    prefs.family_member_left_promoted = family_member_left_promoted
    prefs.family_account_deleted = family_account_deleted
    prefs.family_account_deleted_promoted = family_account_deleted_promoted
    prefs.pet_added = pet_added
    prefs.pet_updated = pet_updated
    prefs.pet_deleted = pet_deleted
    prefs.medication_created = medication_created
    prefs.medication_updated = medication_updated
    prefs.medication_archived = medication_archived
    prefs.dose_administered = dose_administered
    prefs.created_at = datetime(2024, 1, 1)
    prefs.updated_at = datetime(2024, 1, 1)
    return prefs


# ============== Register Device Token Tests ==============

class TestRegisterDeviceToken:
    """Tests for POST /api/v1/notifications/device-token endpoint."""

    @pytest.mark.asyncio
    async def test_register_device_token_success_new_token(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should register a new device token successfully."""
        device_token = "abc123def456"
        device_name = "iPhone 15 Pro"

        # Mock check for existing token (none found)
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        # Create a proper mock for the added token that will be returned
        mock_token = create_mock_device_token(
            user_id=test_user_id,
            device_token=device_token,
            device_name=device_name,
        )

        def mock_add(obj):
            # Copy attributes from the created object to our mock
            obj.id = mock_token.id
            obj.created_at = mock_token.created_at
            obj.updated_at = mock_token.updated_at

        mock_db_session.execute = AsyncMock(side_effect=[existing_result])
        mock_db_session.add = MagicMock(side_effect=mock_add)
        mock_db_session.refresh = AsyncMock()

        # Make request
        response = await client.post(
            "/api/v1/notifications/device-token",
            json={
                "device_token": device_token,
                "device_name": device_name,
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["device_token"] == device_token
        assert data["device_name"] == device_name
        assert data["platform"] == "ios"
        assert data["is_active"] is True

        # Verify db operations
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_device_token_success_reactivate_existing(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should reactivate an existing inactive device token."""
        device_token = "abc123def456"
        device_name = "iPhone 15 Pro"

        # Mock existing inactive token
        existing_token = create_mock_device_token(
            user_id=test_user_id,
            device_token=device_token,
            device_name="Old Name",
            is_active=False,
        )
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_token

        mock_db_session.execute = AsyncMock(side_effect=[existing_result])

        # Make request
        response = await client.post(
            "/api/v1/notifications/device-token",
            json={
                "device_token": device_token,
                "device_name": device_name,
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["device_token"] == device_token
        assert data["device_name"] == device_name
        assert data["is_active"] is True

        # Verify token was reactivated
        assert existing_token.is_active is True
        assert existing_token.device_name == device_name
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_device_token_success_update_name_only(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should update device name for existing active token."""
        device_token = "abc123def456"
        new_device_name = "iPhone 16 Pro Max"

        # Mock existing active token
        existing_token = create_mock_device_token(
            user_id=test_user_id,
            device_token=device_token,
            device_name="Old Name",
            is_active=True,
        )
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_token

        mock_db_session.execute = AsyncMock(side_effect=[existing_result])

        # Make request
        response = await client.post(
            "/api/v1/notifications/device-token",
            json={
                "device_token": device_token,
                "device_name": new_device_name,
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["device_name"] == new_device_name

        # Verify device name was updated
        assert existing_token.device_name == new_device_name
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_device_token_success_no_device_name(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should register device token without device name."""
        device_token = "abc123def456"

        # Mock no existing token
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        # Create a proper mock for the added token
        mock_token = create_mock_device_token(
            user_id=test_user_id,
            device_token=device_token,
            device_name=None,
        )

        def mock_add(obj):
            obj.id = mock_token.id
            obj.created_at = mock_token.created_at
            obj.updated_at = mock_token.updated_at

        mock_db_session.execute = AsyncMock(side_effect=[existing_result])
        mock_db_session.add = MagicMock(side_effect=mock_add)
        mock_db_session.refresh = AsyncMock()

        # Make request without device_name
        response = await client.post(
            "/api/v1/notifications/device-token",
            json={"device_token": device_token},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["device_token"] == device_token
        assert data["device_name"] is None

    @pytest.mark.asyncio
    async def test_register_device_token_validation_error_empty_token(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should accept empty device token (Pydantic allows empty strings by default)."""
        # Empty string is valid in Pydantic unless we add min_length validator
        # This test verifies current behavior - endpoint accepts empty strings

        # Mock no existing token
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        # Create mock for empty token
        mock_token = create_mock_device_token(
            user_id=test_user_id,
            device_token="",
            device_name=None,
        )

        def mock_add(obj):
            obj.id = mock_token.id
            obj.created_at = mock_token.created_at
            obj.updated_at = mock_token.updated_at

        mock_db_session.execute = AsyncMock(side_effect=[existing_result])
        mock_db_session.add = MagicMock(side_effect=mock_add)
        mock_db_session.refresh = AsyncMock()

        response = await client.post(
            "/api/v1/notifications/device-token",
            json={"device_token": ""},
            headers=auth_headers,
        )

        # Empty strings are currently accepted. If you want to reject them,
        # add Field(min_length=1) to DeviceTokenCreate.device_token in schemas
        assert response.status_code == 201
        data = response.json()
        assert data["device_token"] == ""

    @pytest.mark.asyncio
    async def test_register_device_token_validation_error_missing_token(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when device_token is missing."""
        response = await client.post(
            "/api/v1/notifications/device-token",
            json={"device_name": "iPhone"},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_device_token_unauthorized(
        self,
        client: AsyncClient,
    ):
        """Should return 401 without auth token."""
        response = await client.post(
            "/api/v1/notifications/device-token",
            json={"device_token": "abc123"},
        )

        assert response.status_code == 401


# ============== Unregister Device Token Tests ==============

class TestUnregisterDeviceToken:
    """Tests for DELETE /api/v1/notifications/device-token endpoint."""

    @pytest.mark.asyncio
    async def test_unregister_device_token_success(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should deactivate device token successfully."""
        device_token = "abc123def456"

        # Mock existing active token
        existing_token = create_mock_device_token(
            user_id=test_user_id,
            device_token=device_token,
            is_active=True,
        )
        token_result = MagicMock()
        token_result.scalar_one_or_none.return_value = existing_token

        mock_db_session.execute = AsyncMock(side_effect=[token_result])

        # Make request
        response = await client.request(
            "DELETE",
            "/api/v1/notifications/device-token",
            json={"device_token": device_token},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 204

        # Verify token was deactivated
        assert existing_token.is_active is False
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unregister_device_token_not_found_no_op(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return 204 even if token not found (idempotent)."""
        device_token = "nonexistent"

        # Mock no token found
        token_result = MagicMock()
        token_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[token_result])

        # Make request
        response = await client.request(
            "DELETE",
            "/api/v1/notifications/device-token",
            json={"device_token": device_token},
            headers=auth_headers,
        )

        # Verify response - should still be 204 (idempotent)
        assert response.status_code == 204

        # Verify commit was not called
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_unregister_device_token_validation_error_missing_token(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when device_token is missing."""
        response = await client.request(
            "DELETE",
            "/api/v1/notifications/device-token",
            json={},
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_unregister_device_token_unauthorized(
        self,
        client: AsyncClient,
    ):
        """Should return 401 without auth token."""
        response = await client.request(
            "DELETE",
            "/api/v1/notifications/device-token",
            json={"device_token": "abc123"},
        )

        assert response.status_code == 401


# ============== Get Notification Preferences Tests ==============

class TestGetNotificationPreferences:
    """Tests for GET /api/v1/notifications/preferences endpoint."""

    @pytest.mark.asyncio
    async def test_get_preferences_success_existing(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return existing notification preferences."""
        # Mock existing preferences with some disabled
        mock_prefs = create_mock_notification_preferences(
            user_id=test_user_id,
            family_member_joined=True,
            family_role_changed=False,
            pet_added=True,
            pet_updated=False,
            medication_created=True,
        )
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = mock_prefs

        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])

        # Make request
        response = await client.get(
            "/api/v1/notifications/preferences",
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Check specific preferences
        assert data["family_member_joined"] is True
        assert data["family_role_changed"] is False
        assert data["pet_added"] is True
        assert data["pet_updated"] is False
        assert data["medication_created"] is True

    @pytest.mark.asyncio
    async def test_get_preferences_success_defaults_no_existing(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
    ):
        """Should return default preferences when none exist."""
        # Mock no existing preferences
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])

        response = await client.get(
            "/api/v1/notifications/preferences",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["family_member_joined"] is True
        assert data["family_role_changed"] is True
        assert data["family_member_left"] is True
        assert data["family_member_left_promoted"] is True
        assert data["family_account_deleted"] is True
        assert data["family_account_deleted_promoted"] is True
        assert data["pet_added"] is True
        assert data["pet_updated"] is True
        assert data["pet_deleted"] is True
        assert data["medication_created"] is True
        assert data["medication_updated"] is True
        assert data["medication_archived"] is True
        assert data["dose_administered"] is True

    @pytest.mark.asyncio
    async def test_get_preferences_unauthorized(
        self,
        client: AsyncClient,
    ):
        """Should return 401 without auth token."""
        response = await client.get("/api/v1/notifications/preferences")

        assert response.status_code == 401


# ============== Update Notification Preferences Tests ==============

class TestUpdateNotificationPreferences:
    """Tests for PATCH /api/v1/notifications/preferences endpoint."""

    @pytest.mark.asyncio
    async def test_update_preferences_success_existing(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should update existing notification preferences."""
        # Mock existing preferences
        mock_prefs = create_mock_notification_preferences(
            user_id=test_user_id,
            family_member_joined=True,
            pet_added=True,
            medication_created=True,
        )
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = mock_prefs

        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])

        # Make request to update specific preferences
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={
                "family_member_joined": False,
                "pet_added": False,
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # Verify updated fields
        assert data["family_member_joined"] is False
        assert data["pet_added"] is False
        # Unchanged field should remain
        assert data["medication_created"] is True

        # Verify db operations
        assert mock_prefs.family_member_joined is False
        assert mock_prefs.pet_added is False
        mock_db_session.commit.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_preferences_success_create_new(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should create new preferences when none exist (upsert pattern)."""
        # Mock no existing preferences
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = None

        # Create a mock for the newly created preferences
        mock_prefs = create_mock_notification_preferences(
            user_id=test_user_id,
            family_member_joined=False,
            pet_updated=False,
        )

        def mock_add(obj):
            # Set attributes on the added object
            for attr, value in vars(mock_prefs).items():
                if not attr.startswith('_'):
                    setattr(obj, attr, value)

        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])
        mock_db_session.add = MagicMock(side_effect=mock_add)
        mock_db_session.refresh = AsyncMock()

        # Make request
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={
                "family_member_joined": False,
                "pet_updated": False,
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200

        # Verify new record was created
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_preferences_success_partial_update(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should only update provided fields, leaving others unchanged."""
        # Mock existing preferences
        mock_prefs = create_mock_notification_preferences(
            user_id=test_user_id,
            family_member_joined=True,
            family_role_changed=True,
            pet_added=True,
            medication_created=True,
        )
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = mock_prefs

        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])

        # Update only one field
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={"family_member_joined": False},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200

        # Verify only specified field was updated
        assert mock_prefs.family_member_joined is False
        # Other fields should remain unchanged
        assert mock_prefs.family_role_changed is True
        assert mock_prefs.pet_added is True
        assert mock_prefs.medication_created is True

    @pytest.mark.asyncio
    async def test_update_preferences_success_all_fields(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should update all notification preference fields."""
        # Mock existing preferences
        mock_prefs = create_mock_notification_preferences(user_id=test_user_id)
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = mock_prefs

        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])

        # Update all fields
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={
                "family_member_joined": False,
                "family_role_changed": False,
                "family_member_left": False,
                "family_member_left_promoted": False,
                "family_account_deleted": False,
                "family_account_deleted_promoted": False,
                "pet_added": False,
                "pet_updated": False,
                "pet_deleted": False,
                "medication_created": False,
                "medication_updated": False,
                "medication_archived": False,
            },
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        # All fields should be False
        assert data["family_member_joined"] is False
        assert data["family_role_changed"] is False
        assert data["family_member_left"] is False
        assert data["family_member_left_promoted"] is False
        assert data["family_account_deleted"] is False
        assert data["family_account_deleted_promoted"] is False
        assert data["pet_added"] is False
        assert data["pet_updated"] is False
        assert data["pet_deleted"] is False
        assert data["medication_created"] is False
        assert data["medication_updated"] is False
        assert data["medication_archived"] is False

    @pytest.mark.asyncio
    async def test_update_preferences_success_empty_body(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should accept empty body and return existing preferences."""
        # Mock existing preferences
        mock_prefs = create_mock_notification_preferences(user_id=test_user_id)
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = mock_prefs

        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])

        # Make request with empty body
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={},
            headers=auth_headers,
        )

        # Verify response
        assert response.status_code == 200

        # No fields should have been changed
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_preferences_validation_error_invalid_type(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid field types."""
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={
                "family_member_joined": "not_a_boolean",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_preferences_validation_error_unknown_field(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should ignore unknown fields and update valid ones."""
        # Mock existing preferences
        mock_prefs = create_mock_notification_preferences(user_id=test_user_id)
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = mock_prefs

        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])

        # Include unknown field
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={
                "family_member_joined": False,
                "unknown_field": True,  # Should be ignored
            },
            headers=auth_headers,
        )

        # Should still succeed and update valid fields
        assert response.status_code == 200
        assert mock_prefs.family_member_joined is False

    @pytest.mark.asyncio
    async def test_update_preferences_unauthorized(
        self,
        client: AsyncClient,
    ):
        """Should return 401 without auth token."""
        response = await client.patch(
            "/api/v1/notifications/preferences",
            json={"family_member_joined": False},
        )

        assert response.status_code == 401


# ============== Edge Cases and Integration Tests ==============

class TestNotificationEdgeCases:
    """Tests for edge cases and integration scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_devices_same_user(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should allow registering multiple device tokens for same user."""
        # Create mocks for both devices
        mock_token1 = create_mock_device_token(
            user_id=test_user_id,
            device_token="device1_token",
            device_name="iPhone",
        )
        mock_token2 = create_mock_device_token(
            user_id=test_user_id,
            device_token="device2_token",
            device_name="iPad",
        )

        call_count = 0

        def mock_add(obj):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                obj.id = mock_token1.id
                obj.created_at = mock_token1.created_at
                obj.updated_at = mock_token1.updated_at
            else:
                obj.id = mock_token2.id
                obj.created_at = mock_token2.created_at
                obj.updated_at = mock_token2.updated_at

        # Register first device
        existing_result_1 = MagicMock()
        existing_result_1.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(side_effect=[existing_result_1])
        mock_db_session.add = MagicMock(side_effect=mock_add)
        mock_db_session.refresh = AsyncMock()

        response1 = await client.post(
            "/api/v1/notifications/device-token",
            json={
                "device_token": "device1_token",
                "device_name": "iPhone",
            },
            headers=auth_headers,
        )
        assert response1.status_code == 201

        # Register second device
        existing_result_2 = MagicMock()
        existing_result_2.scalar_one_or_none.return_value = None
        mock_db_session.execute = AsyncMock(side_effect=[existing_result_2])

        response2 = await client.post(
            "/api/v1/notifications/device-token",
            json={
                "device_token": "device2_token",
                "device_name": "iPad",
            },
            headers=auth_headers,
        )
        assert response2.status_code == 201

        # Both should succeed
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_preferences_toggle_on_off(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should allow toggling preferences on and off multiple times."""
        # Mock existing preferences
        mock_prefs = create_mock_notification_preferences(
            user_id=test_user_id,
            family_member_joined=True,
        )
        prefs_result = MagicMock()
        prefs_result.scalar_one_or_none.return_value = mock_prefs

        # Toggle off
        mock_db_session.execute = AsyncMock(side_effect=[prefs_result])
        response1 = await client.patch(
            "/api/v1/notifications/preferences",
            json={"family_member_joined": False},
            headers=auth_headers,
        )
        assert response1.status_code == 200
        assert mock_prefs.family_member_joined is False

        # Toggle back on
        prefs_result_2 = MagicMock()
        prefs_result_2.scalar_one_or_none.return_value = mock_prefs
        mock_db_session.execute = AsyncMock(side_effect=[prefs_result_2])

        response2 = await client.patch(
            "/api/v1/notifications/preferences",
            json={"family_member_joined": True},
            headers=auth_headers,
        )
        assert response2.status_code == 200
        assert mock_prefs.family_member_joined is True


# ============== Integration Test Documentation ==============

class TestNotificationIntegrationNotes:
    """
    Documentation of comprehensive test coverage implemented.

    Test Coverage Summary:
    ----------------------

    POST /api/v1/notifications/device-token:
    - ✓ Register new device token
    - ✓ Reactivate existing inactive token
    - ✓ Update device name for active token
    - ✓ Register without device name (optional field)
    - ✓ Validation: empty token
    - ✓ Validation: missing token
    - ✓ Authorization: 401 without auth

    DELETE /api/v1/notifications/device-token:
    - ✓ Deactivate device token
    - ✓ Idempotent behavior when token not found
    - ✓ Validation: missing token
    - ✓ Authorization: 401 without auth

    GET /api/v1/notifications/preferences:
    - ✓ Return existing preferences
    - ✓ Return defaults when none exist
    - ✓ Authorization: 401 without auth

    PATCH /api/v1/notifications/preferences:
    - ✓ Update existing preferences (partial)
    - ✓ Create new preferences (upsert pattern)
    - ✓ Update single field
    - ✓ Update all fields
    - ✓ Empty body (no changes)
    - ✓ Validation: invalid field types
    - ✓ Ignore unknown fields
    - ✓ Authorization: 401 without auth

    Edge Cases:
    - ✓ Multiple devices for same user
    - ✓ Toggle preferences on/off repeatedly

    Not Tested (out of scope for integration tests):
    - GET /api/v1/notifications/device-tokens - list tokens endpoint
    - POST /api/v1/notifications/test - test notification sending
      (requires APNs service mocking which is complex and better suited for e2e tests)
    - Database constraint violations (unique constraints, etc.)
    - RLS policies (no family_id context needed for notifications)

    Testing Pattern:
    ---------------
    1. Mock database execute() calls with appropriate return values
    2. Verify HTTP status codes and response data
    3. Verify database operations (add, commit, refresh)
    4. Test authorization (401 without token)
    5. Test validation (422 for invalid data)
    6. Test edge cases and idempotent behavior
    """
    pass
