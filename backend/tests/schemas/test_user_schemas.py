"""
Tests for User and Auth Pydantic schemas.

Validates user/auth schema behavior to prevent breaking changes to iOS app.
"""
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.endpoints.auth import (
    AppleAuthRequest,
    FamilyResponse,
    UserResponse,
    AuthResponse,
    MeResponse,
    ProfileUpdateRequest,
    DeleteAccountRequest,
    DeleteAccountResponse,
    DevLoginRequest,
)


class TestAppleAuthRequest:
    """Tests for AppleAuthRequest schema."""

    def test_apple_auth_request_required_fields_only(self):
        """Should create request with only required fields."""
        request = AppleAuthRequest(
            identity_token="mock_jwt_token_from_apple",
            user_id="000123.abc456def789.1234",
        )

        assert request.identity_token == "mock_jwt_token_from_apple"
        assert request.user_id == "000123.abc456def789.1234"
        assert request.email is None
        assert request.first_name is None
        assert request.last_name is None

    def test_apple_auth_request_with_all_fields(self):
        """Should create request with all optional fields."""
        request = AppleAuthRequest(
            identity_token="mock_jwt_token",
            user_id="000123.abc456def789.1234",
            email="user@example.com",
            first_name="John",
            last_name="Doe",
        )

        assert request.identity_token == "mock_jwt_token"
        assert request.user_id == "000123.abc456def789.1234"
        assert request.email == "user@example.com"
        assert request.first_name == "John"
        assert request.last_name == "Doe"

    def test_apple_auth_request_missing_identity_token_raises_error(self):
        """Missing identity_token should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AppleAuthRequest(user_id="000123.abc456def789.1234")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("identity_token",) for error in errors)

    def test_apple_auth_request_missing_user_id_raises_error(self):
        """Missing user_id should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AppleAuthRequest(identity_token="mock_jwt_token")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user_id",) for error in errors)

    def test_apple_auth_request_empty_strings_allowed(self):
        """Empty strings should be allowed for optional fields."""
        request = AppleAuthRequest(
            identity_token="mock_jwt_token",
            user_id="000123.abc456def789.1234",
            email="",
            first_name="",
            last_name="",
        )

        assert request.email == ""
        assert request.first_name == ""
        assert request.last_name == ""

    def test_apple_auth_request_first_name_without_last_name(self):
        """Should allow first name without last name."""
        request = AppleAuthRequest(
            identity_token="mock_jwt_token",
            user_id="000123.abc456def789.1234",
            first_name="John",
        )

        assert request.first_name == "John"
        assert request.last_name is None


class TestFamilyResponse:
    """Tests for FamilyResponse schema."""

    def test_family_response_all_fields(self):
        """Should create family response with all required fields."""
        family = FamilyResponse(
            id=str(uuid4()),
            name="Smith Family",
            invite_code="ABC12345",
            role="admin",
        )

        assert family.name == "Smith Family"
        assert family.invite_code == "ABC12345"
        assert family.role == "admin"

    def test_family_response_role_member(self):
        """Should accept 'member' role."""
        family = FamilyResponse(
            id=str(uuid4()),
            name="Test Family",
            invite_code="TEST1234",
            role="member",
        )

        assert family.role == "member"

    def test_family_response_role_admin(self):
        """Should accept 'admin' role."""
        family = FamilyResponse(
            id=str(uuid4()),
            name="Test Family",
            invite_code="TEST1234",
            role="admin",
        )

        assert family.role == "admin"

    def test_family_response_missing_fields_raises_error(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FamilyResponse(
                id=str(uuid4()),
                name="Test Family",
                # Missing invite_code and role
            )

        errors = exc_info.value.errors()
        assert len(errors) == 2

    def test_family_response_id_as_string(self):
        """ID should be stored as string."""
        family_id = str(uuid4())
        family = FamilyResponse(
            id=family_id,
            name="Test Family",
            invite_code="TEST1234",
            role="admin",
        )

        assert family.id == family_id
        assert isinstance(family.id, str)

    def test_family_response_invite_code_format(self):
        """Invite code should accept alphanumeric strings."""
        family = FamilyResponse(
            id=str(uuid4()),
            name="Test Family",
            invite_code="A2B3C4D5",  # Alphanumeric
            role="admin",
        )

        assert family.invite_code == "A2B3C4D5"


class TestUserResponse:
    """Tests for UserResponse schema."""

    def test_user_response_required_fields_only(self):
        """Should create user response with only ID."""
        user = UserResponse(id=str(uuid4()))

        assert user.id is not None
        assert user.email is None
        assert user.first_name is None
        assert user.last_name is None

    def test_user_response_with_all_fields(self):
        """Should create user response with all fields."""
        user_id = str(uuid4())
        user = UserResponse(
            id=user_id,
            email="john@example.com",
            first_name="John",
            last_name="Doe",
        )

        assert user.id == user_id
        assert user.email == "john@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"

    def test_user_response_missing_id_raises_error(self):
        """Missing ID should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserResponse(
                email="john@example.com",
                first_name="John",
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("id",) for error in errors)

    def test_user_response_email_optional(self):
        """Email should be optional."""
        user = UserResponse(
            id=str(uuid4()),
            first_name="John",
            last_name="Doe",
        )

        assert user.email is None
        assert user.first_name == "John"

    def test_user_response_partial_name(self):
        """Should allow first name without last name."""
        user = UserResponse(
            id=str(uuid4()),
            email="john@example.com",
            first_name="John",
        )

        assert user.first_name == "John"
        assert user.last_name is None

    def test_user_response_id_as_string(self):
        """ID should be stored as string."""
        user_id = str(uuid4())
        user = UserResponse(id=user_id)

        assert user.id == user_id
        assert isinstance(user.id, str)


class TestAuthResponse:
    """Tests for AuthResponse schema."""

    def test_auth_response_with_empty_families(self):
        """Should create auth response with empty families list."""
        user_id = str(uuid4())
        response = AuthResponse(
            token="jwt_token_here",
            user=UserResponse(
                id=user_id,
                email="user@example.com",
                first_name="Test",
            ),
            families=[],
        )

        assert response.token == "jwt_token_here"
        assert response.user.id == user_id
        assert response.families == []

    def test_auth_response_with_multiple_families(self):
        """Should create auth response with multiple families."""
        user_id = str(uuid4())
        response = AuthResponse(
            token="jwt_token_here",
            user=UserResponse(
                id=user_id,
                email="user@example.com",
                first_name="Test",
            ),
            families=[
                FamilyResponse(
                    id=str(uuid4()),
                    name="Family 1",
                    invite_code="CODE1234",
                    role="admin",
                ),
                FamilyResponse(
                    id=str(uuid4()),
                    name="Family 2",
                    invite_code="CODE5678",
                    role="member",
                ),
            ],
        )

        assert len(response.families) == 2
        assert response.families[0].name == "Family 1"
        assert response.families[0].role == "admin"
        assert response.families[1].name == "Family 2"
        assert response.families[1].role == "member"

    def test_auth_response_missing_token_raises_error(self):
        """Missing token should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AuthResponse(
                user=UserResponse(id=str(uuid4())),
                families=[],
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("token",) for error in errors)

    def test_auth_response_missing_user_raises_error(self):
        """Missing user should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AuthResponse(
                token="jwt_token_here",
                families=[],
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user",) for error in errors)

    def test_auth_response_missing_families_raises_error(self):
        """Missing families list should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AuthResponse(
                token="jwt_token_here",
                user=UserResponse(id=str(uuid4())),
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("families",) for error in errors)

    def test_auth_response_nested_user_validation(self):
        """Nested user should be properly validated."""
        user_id = str(uuid4())
        response = AuthResponse(
            token="jwt_token_here",
            user=UserResponse(
                id=user_id,
                email="test@example.com",
                first_name="John",
                last_name="Doe",
            ),
            families=[],
        )

        assert response.user.id == user_id
        assert response.user.email == "test@example.com"
        assert response.user.first_name == "John"
        assert response.user.last_name == "Doe"


class TestMeResponse:
    """Tests for MeResponse schema (GET /auth/me)."""

    def test_me_response_with_no_families(self):
        """Should create me response with empty families list."""
        user_id = str(uuid4())
        response = MeResponse(
            user=UserResponse(
                id=user_id,
                email="user@example.com",
                first_name="Test",
            ),
            families=[],
        )

        assert response.user.id == user_id
        assert response.families == []

    def test_me_response_with_families(self):
        """Should create me response with families."""
        user_id = str(uuid4())
        response = MeResponse(
            user=UserResponse(
                id=user_id,
                email="user@example.com",
                first_name="Test",
            ),
            families=[
                FamilyResponse(
                    id=str(uuid4()),
                    name="My Family",
                    invite_code="ABC12345",
                    role="admin",
                ),
            ],
        )

        assert len(response.families) == 1
        assert response.families[0].name == "My Family"

    def test_me_response_missing_user_raises_error(self):
        """Missing user should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MeResponse(families=[])

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user",) for error in errors)

    def test_me_response_missing_families_raises_error(self):
        """Missing families should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            MeResponse(user=UserResponse(id=str(uuid4())))

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("families",) for error in errors)


class TestProfileUpdateRequest:
    """Tests for ProfileUpdateRequest schema."""

    def test_profile_update_required_fields_only(self):
        """Should create request with only first name."""
        request = ProfileUpdateRequest(first_name="John")

        assert request.first_name == "John"
        assert request.last_name is None

    def test_profile_update_with_all_fields(self):
        """Should create request with both names."""
        request = ProfileUpdateRequest(
            first_name="John",
            last_name="Doe",
        )

        assert request.first_name == "John"
        assert request.last_name == "Doe"

    def test_profile_update_missing_first_name_raises_error(self):
        """Missing first_name should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ProfileUpdateRequest(last_name="Doe")

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("first_name",) for error in errors)

    def test_profile_update_empty_first_name_allowed(self):
        """Empty first_name should be allowed (Pydantic default behavior)."""
        request = ProfileUpdateRequest(first_name="", last_name="Doe")

        # Pydantic allows empty strings by default
        assert request.first_name == ""
        assert request.last_name == "Doe"

    def test_profile_update_last_name_can_be_empty_string(self):
        """Last name should accept empty string."""
        request = ProfileUpdateRequest(
            first_name="John",
            last_name="",
        )

        assert request.first_name == "John"
        assert request.last_name == ""

    def test_profile_update_whitespace_names(self):
        """Should accept names with whitespace."""
        request = ProfileUpdateRequest(
            first_name="Mary Jane",
            last_name="Watson-Parker",
        )

        assert request.first_name == "Mary Jane"
        assert request.last_name == "Watson-Parker"


class TestDeleteAccountRequest:
    """Tests for DeleteAccountRequest schema."""

    def test_delete_account_request_no_new_admin(self):
        """Should create request without new admin."""
        request = DeleteAccountRequest()

        assert request.new_admin_user_id is None

    def test_delete_account_request_with_new_admin(self):
        """Should create request with new admin user ID."""
        new_admin_id = str(uuid4())
        request = DeleteAccountRequest(new_admin_user_id=new_admin_id)

        assert request.new_admin_user_id == new_admin_id

    def test_delete_account_request_all_fields_optional(self):
        """All fields should be optional."""
        request = DeleteAccountRequest()

        assert request.new_admin_user_id is None

    def test_delete_account_request_new_admin_as_string(self):
        """New admin ID should be string."""
        new_admin_id = str(uuid4())
        request = DeleteAccountRequest(new_admin_user_id=new_admin_id)

        assert isinstance(request.new_admin_user_id, str)


class TestDeleteAccountResponse:
    """Tests for DeleteAccountResponse schema."""

    def test_delete_account_response_success_with_steps(self):
        """Should create response with success and steps."""
        response = DeleteAccountResponse(
            success=True,
            steps_completed=[
                "deleted_family_123",
                "deleted_device_tokens",
                "deleted_account",
            ],
        )

        assert response.success is True
        assert len(response.steps_completed) == 3
        assert "deleted_account" in response.steps_completed

    def test_delete_account_response_failure_empty_steps(self):
        """Should create response with failure and empty steps."""
        response = DeleteAccountResponse(
            success=False,
            steps_completed=[],
        )

        assert response.success is False
        assert response.steps_completed == []

    def test_delete_account_response_missing_success_raises_error(self):
        """Missing success should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DeleteAccountResponse(steps_completed=[])

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("success",) for error in errors)

    def test_delete_account_response_missing_steps_raises_error(self):
        """Missing steps_completed should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DeleteAccountResponse(success=True)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("steps_completed",) for error in errors)

    def test_delete_account_response_multiple_steps(self):
        """Should handle multiple steps correctly."""
        response = DeleteAccountResponse(
            success=True,
            steps_completed=[
                "removed_from_family_abc",
                "promoted_admin_and_removed_def",
                "deleted_device_tokens",
                "deleted_account",
            ],
        )

        assert len(response.steps_completed) == 4

    def test_delete_account_response_step_order_preserved(self):
        """Steps order should be preserved."""
        steps = ["step_1", "step_2", "step_3"]
        response = DeleteAccountResponse(
            success=True,
            steps_completed=steps,
        )

        assert response.steps_completed == steps


class TestDevLoginRequestSchema:
    """Tests for DevLoginRequest schema (UI testing)."""

    def test_test_login_request_defaults(self):
        """Should create request with default values."""
        request = DevLoginRequest()

        assert request.test_user_id == "ui-test-user"
        assert request.email == "uitest@example.com"
        assert request.first_name == "UI"
        assert request.last_name == "Tester"
        assert request.create_family is False
        assert request.family_name == "Test Family"

    def test_test_login_request_custom_values(self):
        """Should create request with custom values."""
        request = DevLoginRequest(
            test_user_id="custom-user-123",
            email="custom@test.com",
            first_name="Custom",
            last_name="User",
            create_family=True,
            family_name="Custom Family",
        )

        assert request.test_user_id == "custom-user-123"
        assert request.email == "custom@test.com"
        assert request.first_name == "Custom"
        assert request.last_name == "User"
        assert request.create_family is True
        assert request.family_name == "Custom Family"

    def test_test_login_request_create_family_flag(self):
        """Should accept create_family boolean."""
        request_false = DevLoginRequest(create_family=False)
        request_true = DevLoginRequest(create_family=True)

        assert request_false.create_family is False
        assert request_true.create_family is True

    def test_test_login_request_partial_override(self):
        """Should allow partial override of defaults."""
        request = DevLoginRequest(
            test_user_id="user-456",
            create_family=True,
        )

        assert request.test_user_id == "user-456"
        assert request.email == "uitest@example.com"  # Default
        assert request.first_name == "UI"  # Default
        assert request.create_family is True

    def test_test_login_request_all_fields_optional(self):
        """All fields should have defaults."""
        request = DevLoginRequest()

        # Should not raise - all fields have defaults
        assert request is not None

    def test_test_login_request_family_name_for_creation(self):
        """Family name should be used when create_family is True."""
        request = DevLoginRequest(
            create_family=True,
            family_name="My Test Family",
        )

        assert request.create_family is True
        assert request.family_name == "My Test Family"


class TestSchemaInteroperability:
    """Tests for schema interoperability and nested validation."""

    def test_auth_response_complete_flow(self):
        """Should create complete auth response with all nested schemas."""
        user_id = str(uuid4())
        family_id_1 = str(uuid4())
        family_id_2 = str(uuid4())

        response = AuthResponse(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            user=UserResponse(
                id=user_id,
                email="john.doe@example.com",
                first_name="John",
                last_name="Doe",
            ),
            families=[
                FamilyResponse(
                    id=family_id_1,
                    name="Doe Family",
                    invite_code="DOEABC12",
                    role="admin",
                ),
                FamilyResponse(
                    id=family_id_2,
                    name="Extended Family",
                    invite_code="EXTFAM99",
                    role="member",
                ),
            ],
        )

        # Verify top-level fields
        assert response.token.startswith("eyJ")
        assert response.user.id == user_id

        # Verify nested user
        assert response.user.email == "john.doe@example.com"
        assert response.user.first_name == "John"

        # Verify nested families
        assert len(response.families) == 2
        assert response.families[0].id == family_id_1
        assert response.families[0].role == "admin"
        assert response.families[1].id == family_id_2
        assert response.families[1].role == "member"

    def test_me_response_matches_auth_response_structure(self):
        """MeResponse should have same structure as AuthResponse minus token."""
        user_id = str(uuid4())
        family_id = str(uuid4())

        me_response = MeResponse(
            user=UserResponse(
                id=user_id,
                email="test@example.com",
                first_name="Test",
            ),
            families=[
                FamilyResponse(
                    id=family_id,
                    name="Test Family",
                    invite_code="TEST1234",
                    role="admin",
                ),
            ],
        )

        # Same fields as AuthResponse except token
        assert me_response.user.id == user_id
        assert len(me_response.families) == 1
        assert me_response.families[0].id == family_id

    def test_user_response_consistency_across_schemas(self):
        """UserResponse should work consistently in AuthResponse and MeResponse."""
        user_id = str(uuid4())
        user = UserResponse(
            id=user_id,
            email="test@example.com",
            first_name="Test",
            last_name="User",
        )

        auth_response = AuthResponse(
            token="token",
            user=user,
            families=[],
        )

        me_response = MeResponse(
            user=user,
            families=[],
        )

        # Both should have same user structure
        assert auth_response.user.id == me_response.user.id
        assert auth_response.user.email == me_response.user.email
        assert auth_response.user.first_name == me_response.user.first_name
