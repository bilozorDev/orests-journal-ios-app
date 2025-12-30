"""
Tests for Family Pydantic schemas.

Validates family schema behavior to prevent breaking changes to iOS app.
"""
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.endpoints.families import (
    CreateFamilyRequest,
    JoinFamilyRequest,
    UpdateFamilyRequest,
    UpdateRoleRequest,
    FamilyMemberResponse,
    FamilyDetailResponse,
    FamilyResponse,
    JoinFamilyResponse,
    LeaveFamilyRequest,
    LeaveFamilyResponse,
)


class TestCreateFamilyRequest:
    """Tests for CreateFamilyRequest schema."""

    def test_create_family_request_with_name(self):
        """Should create request with valid family name."""
        request = CreateFamilyRequest(name="Smith Family")
        assert request.name == "Smith Family"

    def test_create_family_request_empty_name_allowed(self):
        """Empty name should be allowed (validation happens at API level)."""
        request = CreateFamilyRequest(name="")
        assert request.name == ""

    def test_create_family_request_name_with_special_chars(self):
        """Should accept family names with special characters."""
        special_names = [
            "O'Brien Family",
            "Smith & Jones",
            "Family #1",
            "Family (West Coast)",
            "家族",  # Chinese characters
            "Familia López",  # Accented characters
        ]

        for name in special_names:
            request = CreateFamilyRequest(name=name)
            assert request.name == name

    def test_create_family_request_missing_name_raises_error(self):
        """Missing name field should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CreateFamilyRequest()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert errors[0]["type"] == "missing"

    def test_create_family_request_long_name(self):
        """Should accept long family names."""
        long_name = "A" * 255
        request = CreateFamilyRequest(name=long_name)
        assert request.name == long_name


class TestJoinFamilyRequest:
    """Tests for JoinFamilyRequest schema."""

    def test_join_family_request_with_invite_code(self):
        """Should create request with valid invite code."""
        request = JoinFamilyRequest(invite_code="ABCD1234")
        assert request.invite_code == "ABCD1234"

    def test_join_family_request_lowercase_invite_code(self):
        """Should accept lowercase invite codes."""
        request = JoinFamilyRequest(invite_code="abcd1234")
        assert request.invite_code == "abcd1234"

    def test_join_family_request_mixed_case_invite_code(self):
        """Should accept mixed case invite codes."""
        request = JoinFamilyRequest(invite_code="AbCd1234")
        assert request.invite_code == "AbCd1234"

    def test_join_family_request_with_whitespace(self):
        """Should accept invite codes with whitespace (trimmed at API level)."""
        request = JoinFamilyRequest(invite_code=" ABCD1234 ")
        assert request.invite_code == " ABCD1234 "

    def test_join_family_request_missing_invite_code_raises_error(self):
        """Missing invite_code field should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            JoinFamilyRequest()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("invite_code",)
        assert errors[0]["type"] == "missing"


class TestUpdateFamilyRequest:
    """Tests for UpdateFamilyRequest schema."""

    def test_update_family_request_with_name(self):
        """Should create request with new family name."""
        request = UpdateFamilyRequest(name="Updated Family Name")
        assert request.name == "Updated Family Name"

    def test_update_family_request_empty_name_allowed(self):
        """Empty name should be allowed (validation happens at API level)."""
        request = UpdateFamilyRequest(name="")
        assert request.name == ""

    def test_update_family_request_missing_name_raises_error(self):
        """Missing name field should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateFamilyRequest()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("name",)
        assert errors[0]["type"] == "missing"


class TestUpdateRoleRequest:
    """Tests for UpdateRoleRequest schema with Literal type."""

    def test_update_role_request_admin_role(self):
        """Should accept 'admin' role."""
        request = UpdateRoleRequest(role="admin")
        assert request.role == "admin"

    def test_update_role_request_member_role(self):
        """Should accept 'member' role."""
        request = UpdateRoleRequest(role="member")
        assert request.role == "member"

    def test_update_role_request_invalid_role_raises_error(self):
        """Invalid role should raise ValidationError."""
        invalid_roles = ["owner", "guest", "viewer", "moderator", "ADMIN", "Member"]

        for invalid_role in invalid_roles:
            with pytest.raises(ValidationError) as exc_info:
                UpdateRoleRequest(role=invalid_role)

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["loc"] == ("role",)
            # Pydantic v2 uses 'literal_error' for Literal type mismatches
            assert errors[0]["type"] in ["literal_error", "enum"]

    def test_update_role_request_missing_role_raises_error(self):
        """Missing role field should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UpdateRoleRequest()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("role",)
        assert errors[0]["type"] == "missing"

    def test_update_role_request_case_sensitive(self):
        """Role values should be case-sensitive."""
        with pytest.raises(ValidationError):
            UpdateRoleRequest(role="ADMIN")

        with pytest.raises(ValidationError):
            UpdateRoleRequest(role="Member")


class TestFamilyMemberResponse:
    """Tests for FamilyMemberResponse schema."""

    def test_family_member_response_required_fields(self):
        """Should create response with all required fields."""
        member_id = str(uuid4())
        user_id = str(uuid4())
        joined_at = datetime.now(UTC)

        response = FamilyMemberResponse(
            id=member_id,
            user_id=user_id,
            role="member",
            joined_at=joined_at,
        )

        assert response.id == member_id
        assert response.user_id == user_id
        assert response.role == "member"
        assert response.joined_at == joined_at
        assert response.email is None
        assert response.first_name is None
        assert response.last_name is None

    def test_family_member_response_with_all_fields(self):
        """Should create response with all optional fields."""
        member_id = str(uuid4())
        user_id = str(uuid4())
        joined_at = datetime.now(UTC)

        response = FamilyMemberResponse(
            id=member_id,
            user_id=user_id,
            email="test@example.com",
            first_name="John",
            last_name="Doe",
            role="admin",
            joined_at=joined_at,
        )

        assert response.id == member_id
        assert response.user_id == user_id
        assert response.email == "test@example.com"
        assert response.first_name == "John"
        assert response.last_name == "Doe"
        assert response.role == "admin"
        assert response.joined_at == joined_at

    def test_family_member_response_partial_user_info(self):
        """Should handle partial user information."""
        response = FamilyMemberResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            email="test@example.com",
            first_name=None,
            last_name=None,
            role="member",
            joined_at=datetime.now(UTC),
        )

        assert response.email == "test@example.com"
        assert response.first_name is None
        assert response.last_name is None

    def test_family_member_response_admin_role(self):
        """Should accept admin role."""
        response = FamilyMemberResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            role="admin",
            joined_at=datetime.now(UTC),
        )

        assert response.role == "admin"

    def test_family_member_response_member_role(self):
        """Should accept member role."""
        response = FamilyMemberResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            role="member",
            joined_at=datetime.now(UTC),
        )

        assert response.role == "member"


class TestFamilyDetailResponse:
    """Tests for FamilyDetailResponse schema."""

    def test_family_detail_response_with_no_members(self):
        """Should create response with empty members list."""
        family_id = str(uuid4())
        created_at = datetime.now(UTC)

        response = FamilyDetailResponse(
            id=family_id,
            name="Test Family",
            invite_code="ABCD1234",
            created_at=created_at,
            members=[],
        )

        assert response.id == family_id
        assert response.name == "Test Family"
        assert response.invite_code == "ABCD1234"
        assert response.created_at == created_at
        assert response.members == []

    def test_family_detail_response_with_members(self):
        """Should create response with multiple members."""
        family_id = str(uuid4())
        created_at = datetime.now(UTC)

        members = [
            FamilyMemberResponse(
                id=str(uuid4()),
                user_id=str(uuid4()),
                email="admin@example.com",
                first_name="Admin",
                last_name="User",
                role="admin",
                joined_at=created_at,
            ),
            FamilyMemberResponse(
                id=str(uuid4()),
                user_id=str(uuid4()),
                email="member@example.com",
                first_name="Regular",
                last_name="Member",
                role="member",
                joined_at=created_at,
            ),
        ]

        response = FamilyDetailResponse(
            id=family_id,
            name="Test Family",
            invite_code="ABCD1234",
            created_at=created_at,
            members=members,
        )

        assert len(response.members) == 2
        assert response.members[0].role == "admin"
        assert response.members[1].role == "member"

    def test_family_detail_response_invite_code_format(self):
        """Should accept various invite code formats."""
        invite_codes = [
            "ABCD1234",
            "12345678",
            "ZZZZZZZZ",
            "A1B2C3D4",
        ]

        for code in invite_codes:
            response = FamilyDetailResponse(
                id=str(uuid4()),
                name="Test Family",
                invite_code=code,
                created_at=datetime.now(UTC),
                members=[],
            )
            assert response.invite_code == code


class TestFamilyResponse:
    """Tests for FamilyResponse schema."""

    def test_family_response_all_required_fields(self):
        """Should create response with all required fields."""
        family_id = str(uuid4())

        response = FamilyResponse(
            id=family_id,
            name="Test Family",
            invite_code="ABCD1234",
            role="admin",
        )

        assert response.id == family_id
        assert response.name == "Test Family"
        assert response.invite_code == "ABCD1234"
        assert response.role == "admin"

    def test_family_response_admin_role(self):
        """Should accept admin role for user's role in family."""
        response = FamilyResponse(
            id=str(uuid4()),
            name="Test Family",
            invite_code="ABCD1234",
            role="admin",
        )

        assert response.role == "admin"

    def test_family_response_member_role(self):
        """Should accept member role for user's role in family."""
        response = FamilyResponse(
            id=str(uuid4()),
            name="Test Family",
            invite_code="ABCD1234",
            role="member",
        )

        assert response.role == "member"


class TestJoinFamilyResponse:
    """Tests for JoinFamilyResponse schema."""

    def test_join_family_response_all_fields(self):
        """Should create response with family and message."""
        family = FamilyResponse(
            id=str(uuid4()),
            name="Test Family",
            invite_code="ABCD1234",
            role="member",
        )

        response = JoinFamilyResponse(
            family=family,
            message="Successfully joined Test Family!",
        )

        assert response.family.id == family.id
        assert response.family.name == "Test Family"
        assert response.family.role == "member"
        assert response.message == "Successfully joined Test Family!"

    def test_join_family_response_nested_family_data(self):
        """Should properly nest FamilyResponse within JoinFamilyResponse."""
        response = JoinFamilyResponse(
            family=FamilyResponse(
                id=str(uuid4()),
                name="Smith Family",
                invite_code="SMITH123",
                role="member",
            ),
            message="Welcome!",
        )

        assert isinstance(response.family, FamilyResponse)
        assert response.family.name == "Smith Family"
        assert response.family.invite_code == "SMITH123"


class TestLeaveFamilyRequest:
    """Tests for LeaveFamilyRequest schema."""

    def test_leave_family_request_no_new_admin(self):
        """Should create request without new admin (all fields optional)."""
        request = LeaveFamilyRequest()
        assert request.new_admin_user_id is None

    def test_leave_family_request_with_new_admin(self):
        """Should create request with new admin user ID."""
        new_admin_id = str(uuid4())
        request = LeaveFamilyRequest(new_admin_user_id=new_admin_id)
        assert request.new_admin_user_id == new_admin_id

    def test_leave_family_request_explicit_none(self):
        """Should accept explicit None for new_admin_user_id."""
        request = LeaveFamilyRequest(new_admin_user_id=None)
        assert request.new_admin_user_id is None


class TestLeaveFamilyResponse:
    """Tests for LeaveFamilyResponse schema with Literal action."""

    def test_leave_family_response_left_action(self):
        """Should accept 'left' action."""
        response = LeaveFamilyResponse(
            success=True,
            action="left",
            family_name="Test Family",
        )

        assert response.success is True
        assert response.action == "left"
        assert response.family_name == "Test Family"

    def test_leave_family_response_left_promoted_action(self):
        """Should accept 'left_promoted' action."""
        response = LeaveFamilyResponse(
            success=True,
            action="left_promoted",
            family_name="Test Family",
        )

        assert response.success is True
        assert response.action == "left_promoted"
        assert response.family_name == "Test Family"

    def test_leave_family_response_family_deleted_action(self):
        """Should accept 'family_deleted' action."""
        response = LeaveFamilyResponse(
            success=True,
            action="family_deleted",
            family_name="Test Family",
        )

        assert response.success is True
        assert response.action == "family_deleted"
        assert response.family_name == "Test Family"

    def test_leave_family_response_invalid_action_raises_error(self):
        """Invalid action should raise ValidationError."""
        invalid_actions = [
            "removed",
            "kicked",
            "deleted",
            "LEFT",  # Case-sensitive
            "left_deleted",
        ]

        for invalid_action in invalid_actions:
            with pytest.raises(ValidationError) as exc_info:
                LeaveFamilyResponse(
                    success=True,
                    action=invalid_action,
                    family_name="Test Family",
                )

            errors = exc_info.value.errors()
            assert len(errors) == 1
            assert errors[0]["loc"] == ("action",)
            assert errors[0]["type"] in ["literal_error", "enum"]

    def test_leave_family_response_success_false(self):
        """Should accept success=False."""
        response = LeaveFamilyResponse(
            success=False,
            action="left",
            family_name="Test Family",
        )

        assert response.success is False

    def test_leave_family_response_all_action_types_valid(self):
        """All three action types should be valid."""
        valid_actions = ["left", "left_promoted", "family_deleted"]

        for action in valid_actions:
            response = LeaveFamilyResponse(
                success=True,
                action=action,
                family_name="Test Family",
            )
            assert response.action == action


class TestSchemaFieldTypes:
    """Tests for field type validation across all family schemas."""

    def test_family_member_response_id_accepts_string(self):
        """FamilyMemberResponse ID fields should accept strings."""
        response = FamilyMemberResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            role="member",
            joined_at=datetime.now(UTC),
        )

        assert isinstance(response.id, str)
        assert isinstance(response.user_id, str)

    def test_family_detail_response_id_accepts_string(self):
        """FamilyDetailResponse ID should accept string."""
        response = FamilyDetailResponse(
            id=str(uuid4()),
            name="Test",
            invite_code="ABCD1234",
            created_at=datetime.now(UTC),
            members=[],
        )

        assert isinstance(response.id, str)

    def test_family_response_id_accepts_string(self):
        """FamilyResponse ID should accept string."""
        response = FamilyResponse(
            id=str(uuid4()),
            name="Test",
            invite_code="ABCD1234",
            role="admin",
        )

        assert isinstance(response.id, str)

    def test_datetime_fields_accept_datetime_objects(self):
        """DateTime fields should accept datetime objects."""
        now = datetime.now(UTC)

        member = FamilyMemberResponse(
            id=str(uuid4()),
            user_id=str(uuid4()),
            role="member",
            joined_at=now,
        )

        family_detail = FamilyDetailResponse(
            id=str(uuid4()),
            name="Test",
            invite_code="ABCD1234",
            created_at=now,
            members=[],
        )

        assert isinstance(member.joined_at, datetime)
        assert isinstance(family_detail.created_at, datetime)


class TestSchemaEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_family_name_unicode_characters(self):
        """Should handle various unicode characters in family names."""
        unicode_names = [
            "😀 Happy Family",
            "Müller Familie",
            "Смирнов",  # Cyrillic
            "家族",  # Japanese
            "משפחה",  # Hebrew
        ]

        for name in unicode_names:
            request = CreateFamilyRequest(name=name)
            assert request.name == name

    def test_empty_members_list_valid(self):
        """Empty members list should be valid for FamilyDetailResponse."""
        response = FamilyDetailResponse(
            id=str(uuid4()),
            name="Test Family",
            invite_code="ABCD1234",
            created_at=datetime.now(UTC),
            members=[],
        )

        assert response.members == []
        assert isinstance(response.members, list)

    def test_invite_code_various_lengths(self):
        """Should accept invite codes of various lengths."""
        # Standard is 8 chars, but schema doesn't enforce length
        codes = ["A", "AB", "ABC", "ABCD1234", "ABCD123456789"]

        for code in codes:
            response = FamilyResponse(
                id=str(uuid4()),
                name="Test",
                invite_code=code,
                role="admin",
            )
            assert response.invite_code == code

    def test_optional_fields_none_vs_missing(self):
        """Optional fields should handle None and missing equivalently."""
        # Explicit None
        request1 = LeaveFamilyRequest(new_admin_user_id=None)
        # Omitted (default None)
        request2 = LeaveFamilyRequest()

        assert request1.new_admin_user_id == request2.new_admin_user_id
        assert request1.new_admin_user_id is None
