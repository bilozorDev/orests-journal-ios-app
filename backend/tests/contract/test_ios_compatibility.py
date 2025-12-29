"""
Contract tests to ensure iOS app compatibility.

These tests validate that API response schemas don't break the iOS app by:
1. Verifying enum values match iOS Swift enums
2. Ensuring required fields remain required
3. Validating JSON key format (snake_case not camelCase)
4. Checking date formats are ISO8601
5. Confirming optional fields can be null

CRITICAL: Failures in these tests indicate breaking changes that will crash the iOS app.
"""
from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.medication import (
    MedicationType,
    MedicationResponse,
    MedicationCreate,
    MedicationPhotoResponse,
    DoseDetailResponse,
)
from app.schemas.notification import (
    DeviceTokenResponse,
    NotificationPreferencesResponse,
)
from app.schemas.pet import PetResponse


class TestMedicationContract:
    """Contract tests for medication schemas - ensures iOS app compatibility."""

    def test_medication_type_enum_matches_ios(self):
        """
        iOS MedicationType enum must exactly match backend.

        iOS Swift enum (MedicationModels.swift):
        enum MedicationType: String, Codable {
            case drops, pill, inhaler, shot, liquid, tablet, capsule, topical
        }
        """
        expected_ios_values = {
            "drops", "pill", "inhaler", "shot",
            "liquid", "tablet", "capsule", "topical"
        }

        actual_backend_values = {e.value for e in MedicationType}

        assert actual_backend_values == expected_ios_values, \
            f"MedicationType enum mismatch will crash iOS app! " \
            f"Missing in backend: {expected_ios_values - actual_backend_values}, " \
            f"Extra in backend: {actual_backend_values - expected_ios_values}"

    def test_medication_response_required_fields_cannot_be_null(self):
        """
        iOS Medication struct has non-optional fields that must always be present.

        iOS struct (MedicationModels.swift):
        struct Medication: Codable {
            let id: UUID
            let petId: UUID
            let name: String
            let medicationType: MedicationType
            let startDate: Date
            let timesPerDay: Int
            let createdAt: Date
            // ... optional fields
        }

        Making these fields optional or nullable will crash the iOS app.
        """
        # Missing required field should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            MedicationResponse(
                id=uuid4(),
                pet_id=uuid4(),
                name="Test",
                medication_type=MedicationType.PILL,
                # Missing start_date - REQUIRED field
                times_per_day=1,
                created_at=datetime.utcnow(),
            )

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("start_date",) for err in errors), \
            "start_date must be required for iOS compatibility"

    def test_medication_response_json_uses_snake_case_keys(self):
        """
        iOS APIClient expects snake_case JSON keys and converts to camelCase.

        iOS APIClient.swift automatically converts:
        - "pet_id" -> petId
        - "medication_type" -> medicationType
        - "created_at" -> createdAt

        If backend returns camelCase keys, iOS will fail to decode.
        """
        med = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Test Med",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            times_per_day=2,
            created_at=datetime.utcnow(),
        )

        # Serialize to dict (as JSON would)
        json_dict = med.model_dump(mode='json')

        # MUST have snake_case keys
        required_snake_case_keys = [
            "pet_id",
            "medication_type",
            "start_date",
            "end_date",
            "times_per_day",
            "is_as_needed",
            "reminders_enabled",
            "is_archived",
            "created_by",
            "created_at",
        ]

        for key in required_snake_case_keys:
            assert key in json_dict, \
                f"Missing snake_case key '{key}' - iOS app expects this format"

        # MUST NOT have camelCase keys
        forbidden_camel_case_keys = [
            "petId", "medicationType", "startDate", "endDate",
            "timesPerDay", "isAsNeeded", "remindersEnabled",
            "isArchived", "createdBy", "createdAt",
        ]

        for key in forbidden_camel_case_keys:
            assert key not in json_dict, \
                f"Found camelCase key '{key}' - iOS APIClient expects snake_case"

    def test_medication_response_dates_are_iso8601_serializable(self):
        """
        iOS Date decoder expects ISO8601 format with 'Z' timezone indicator.

        iOS uses ISO8601DateFormatter which requires format:
        - "2024-01-15T14:30:00Z" ✅
        - "2024-01-15 14:30:00" ❌ (will fail to decode)
        """
        med = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Test",
            medication_type=MedicationType.PILL,
            start_date=datetime(2024, 1, 15, 14, 30, 0),
            times_per_day=1,
            created_at=datetime(2024, 1, 15, 10, 0, 0),
        )

        json_dict = med.model_dump(mode='json')

        # Dates should be serialized as ISO8601 strings
        assert isinstance(json_dict["start_date"], str), \
            "Dates must be serialized as strings for iOS"

        # Should be parseable by datetime.fromisoformat
        try:
            parsed_date = datetime.fromisoformat(
                json_dict["start_date"].replace('Z', '+00:00')
            )
            assert parsed_date is not None
        except ValueError:
            pytest.fail("Date format is not ISO8601 compatible with iOS")

    def test_medication_optional_fields_can_be_null(self):
        """
        iOS optional fields must be able to receive null/nil.

        iOS struct:
        struct Medication: Codable {
            let dosage: String?  // Optional
            let endDate: Date?   // Optional
            let notes: String?   // Optional
        }

        If backend sends non-null for these, iOS can handle it.
        If backend sends null, iOS MUST be able to handle it.
        """
        # Create medication with all optional fields as None
        med = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Test",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            times_per_day=1,
            created_at=datetime.utcnow(),
            dosage=None,
            end_date=None,
            notes=None,
            created_by=None,
        )

        json_dict = med.model_dump(mode='json')

        # These fields should be null in JSON
        assert json_dict["dosage"] is None
        assert json_dict["end_date"] is None
        assert json_dict["notes"] is None
        assert json_dict["created_by"] is None

    def test_medication_photo_response_snake_case(self):
        """Medication photo responses must use snake_case."""
        photo = MedicationPhotoResponse(
            id=uuid4(),
            medication_id=uuid4(),
            photo_url="https://example.com/photo.jpg",
            sort_order=0,
            created_at=datetime.utcnow(),
        )

        json_dict = photo.model_dump(mode='json')

        assert "medication_id" in json_dict
        assert "photo_url" in json_dict
        assert "sort_order" in json_dict
        assert "created_at" in json_dict

        # No camelCase
        assert "medicationId" not in json_dict
        assert "photoUrl" not in json_dict
        assert "sortOrder" not in json_dict


class TestDoseContract:
    """Contract tests for dose schemas."""

    def test_dose_detail_response_given_by_is_string_not_uuid(self):
        """
        iOS expects given_by to be a formatted name string, NOT a UUID.

        iOS struct (MedicationModels.swift):
        struct Dose: Codable {
            let givenBy: String  // "You" or "John Doe", NOT UUID
        }

        Backend formats the user name before sending to iOS.
        """
        dose = DoseDetailResponse(
            id=uuid4(),
            medication_id=uuid4(),
            given_at=datetime.utcnow(),
            given_by="You",  # String, not UUID
            notes=None,
            created_at=datetime.utcnow(),
        )

        assert isinstance(dose.given_by, str)

        json_dict = dose.model_dump(mode='json')
        assert isinstance(json_dict["given_by"], str), \
            "iOS expects given_by as string (formatted name), not UUID"

    def test_dose_response_snake_case_keys(self):
        """Dose responses must use snake_case."""
        dose = DoseDetailResponse(
            id=uuid4(),
            medication_id=uuid4(),
            given_at=datetime.utcnow(),
            given_by="Test User",
            notes="Test notes",
            created_at=datetime.utcnow(),
        )

        json_dict = dose.model_dump(mode='json')

        assert "medication_id" in json_dict
        assert "given_at" in json_dict
        assert "given_by" in json_dict
        assert "created_at" in json_dict

        # No camelCase
        assert "medicationId" not in json_dict
        assert "givenAt" not in json_dict
        assert "givenBy" not in json_dict


class TestNotificationContract:
    """Contract tests for notification schemas."""

    def test_device_token_response_snake_case(self):
        """Device token responses must use snake_case."""
        token = DeviceTokenResponse(
            id=uuid4(),
            user_id=uuid4(),
            device_token="mock-token-12345",
            device_name="iPhone 15 Pro",
            platform="ios",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        json_dict = token.model_dump(mode='json')

        assert "user_id" in json_dict
        assert "device_token" in json_dict
        assert "device_name" in json_dict
        assert "is_active" in json_dict
        assert "created_at" in json_dict
        assert "updated_at" in json_dict

        # No camelCase
        assert "userId" not in json_dict
        assert "deviceToken" not in json_dict
        assert "deviceName" not in json_dict
        assert "isActive" not in json_dict

    def test_notification_preferences_all_boolean_types(self):
        """
        iOS expects all notification preference fields to be Bool, not Int.

        iOS struct (NotificationModels.swift):
        struct NotificationPreferences: Codable {
            let familyMemberJoined: Bool  // NOT Int
            // ... all Bool
        }

        Sending 0/1 instead of true/false will crash the decoder.
        """
        prefs = NotificationPreferencesResponse(
            family_member_joined=True,
            family_role_changed=False,
            family_member_left=True,
            family_member_left_promoted=True,
            family_account_deleted=True,
            family_account_deleted_promoted=True,
            pet_added=True,
            pet_updated=False,
            pet_deleted=True,
            medication_created=True,
            medication_updated=True,
            medication_archived=False,
        )

        json_dict = prefs.model_dump(mode='json')

        # All values must be bool (true/false), not int (0/1)
        for key, value in json_dict.items():
            assert isinstance(value, bool), \
                f"Field '{key}' must be bool for iOS, got {type(value)}"

    def test_notification_preferences_has_all_required_fields(self):
        """
        iOS expects exactly 12 notification preference fields.

        Adding/removing fields will break iOS decoding.
        """
        prefs = NotificationPreferencesResponse(
            family_member_joined=True,
            family_role_changed=True,
            family_member_left=True,
            family_member_left_promoted=True,
            family_account_deleted=True,
            family_account_deleted_promoted=True,
            pet_added=True,
            pet_updated=True,
            pet_deleted=True,
            medication_created=True,
            medication_updated=True,
            medication_archived=True,
        )

        json_dict = prefs.model_dump(mode='json')

        expected_fields = {
            "family_member_joined",
            "family_role_changed",
            "family_member_left",
            "family_member_left_promoted",
            "family_account_deleted",
            "family_account_deleted_promoted",
            "pet_added",
            "pet_updated",
            "pet_deleted",
            "medication_created",
            "medication_updated",
            "medication_archived",
        }

        actual_fields = set(json_dict.keys())

        assert actual_fields == expected_fields, \
            f"Notification preferences field mismatch! " \
            f"Missing: {expected_fields - actual_fields}, " \
            f"Extra: {actual_fields - expected_fields}"


class TestPetContract:
    """Contract tests for pet schemas (verify date_of_birth compatibility)."""

    def test_pet_response_date_of_birth_nullable(self):
        """
        iOS Pet struct has optional date_of_birth.

        iOS struct (PetModels.swift):
        struct Pet: Codable {
            let dateOfBirth: Date?  // Optional
        }

        Must be able to handle null.
        """
        from datetime import date
        from app.schemas.pet import PetResponse

        # Pet without date_of_birth
        pet = PetResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Buddy",
            kind="dog",
            photo_url=None,
            current_weight=None,
            date_of_birth=None,  # Null
            created_at=datetime.utcnow(),
            created_by=None,
        )

        json_dict = pet.model_dump(mode='json')
        assert json_dict["date_of_birth"] is None

    def test_pet_response_snake_case_keys(self):
        """Pet responses must use snake_case."""
        from datetime import date
        from app.schemas.pet import PetResponse

        pet = PetResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Buddy",
            kind="dog",
            photo_url="https://example.com/photo.jpg",
            current_weight=25.5,
            date_of_birth=date(2020, 6, 15),
            created_at=datetime.utcnow(),
            created_by=uuid4(),
        )

        json_dict = pet.model_dump(mode='json')

        assert "org_id" in json_dict
        assert "photo_url" in json_dict
        assert "current_weight" in json_dict
        assert "date_of_birth" in json_dict
        assert "created_at" in json_dict
        assert "created_by" in json_dict

        # No camelCase
        assert "orgId" not in json_dict
        assert "photoUrl" not in json_dict
        assert "currentWeight" not in json_dict
        assert "dateOfBirth" not in json_dict


class TestFamilyContract:
    """Contract tests for family/user schemas - ensures iOS app compatibility."""

    def test_family_response_snake_case_keys(self):
        """
        iOS FamilyResponse must receive snake_case JSON keys.

        iOS struct (FamilyModels.swift):
        struct Family: Codable {
            let id: String
            let name: String
            let inviteCode: String  // APIClient converts invite_code -> inviteCode
            let role: String
        }

        Backend must send invite_code (not inviteCode).
        """
        from app.api.endpoints.auth import FamilyResponse

        family = FamilyResponse(
            id=str(uuid4()),
            name="Test Family",
            invite_code="ABC12345",
            role="admin",
        )

        json_dict = family.model_dump(mode='json')

        # Must have snake_case
        assert "invite_code" in json_dict

        # Must NOT have camelCase
        assert "inviteCode" not in json_dict

    def test_family_role_enum_matches_ios(self):
        """
        iOS FamilyRole enum must match backend role strings.

        iOS enum (FamilyModels.swift):
        enum FamilyRole: String, Codable {
            case admin = "admin"
            case member = "member"
        }

        Backend sends "admin" or "member" as strings.
        """
        from app.api.endpoints.auth import FamilyResponse

        # Valid roles
        admin_family = FamilyResponse(
            id=str(uuid4()),
            name="Family",
            invite_code="ABC12345",
            role="admin",
        )
        assert admin_family.role == "admin"

        member_family = FamilyResponse(
            id=str(uuid4()),
            name="Family",
            invite_code="ABC12345",
            role="member",
        )
        assert member_family.role == "member"

    def test_user_response_snake_case_keys(self):
        """
        iOS UserResponse must receive snake_case JSON keys.

        iOS struct (AuthModels.swift):
        struct User: Codable {
            let id: String
            let email: String?
            let firstName: String?  // APIClient converts first_name -> firstName
            let lastName: String?   // APIClient converts last_name -> lastName
        }
        """
        from app.api.endpoints.auth import UserResponse

        user = UserResponse(
            id=str(uuid4()),
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )

        json_dict = user.model_dump(mode='json')

        # Must have snake_case
        assert "first_name" in json_dict
        assert "last_name" in json_dict

        # Must NOT have camelCase
        assert "firstName" not in json_dict
        assert "lastName" not in json_dict

    def test_auth_response_has_required_fields(self):
        """
        iOS AuthResponse expects token, user, and families array.

        iOS struct (AuthModels.swift):
        struct AuthResponse: Codable {
            let token: String
            let user: User
            let families: [Family]
        }

        All three fields are required.
        """
        from app.api.endpoints.auth import AuthResponse, UserResponse, FamilyResponse

        auth = AuthResponse(
            token="test-jwt-token",
            user=UserResponse(
                id=str(uuid4()),
                email="test@example.com",
                first_name="Test",
                last_name="User",
            ),
            families=[
                FamilyResponse(
                    id=str(uuid4()),
                    name="Family 1",
                    invite_code="ABC12345",
                    role="admin",
                ),
            ],
        )

        json_dict = auth.model_dump(mode='json')

        assert "token" in json_dict
        assert "user" in json_dict
        assert "families" in json_dict
        assert isinstance(json_dict["families"], list)

    def test_user_optional_fields_can_be_null(self):
        """
        iOS User struct has optional fields that must handle null.

        iOS struct:
        struct User: Codable {
            let email: String?     // Optional
            let firstName: String? // Optional
            let lastName: String?  // Optional
        }
        """
        from app.api.endpoints.auth import UserResponse

        user = UserResponse(
            id=str(uuid4()),
            email=None,
            first_name=None,
            last_name=None,
        )

        json_dict = user.model_dump(mode='json')

        assert json_dict["email"] is None
        assert json_dict["first_name"] is None
        assert json_dict["last_name"] is None


class TestHealthEventContract:
    """Contract tests for health event schemas - ensures iOS app compatibility."""

    def test_health_category_response_snake_case_keys(self):
        """Health category responses must use snake_case."""
        from app.schemas.health import HealthCategoryResponse

        category = HealthCategoryResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Vomiting",
            name_normalized="vomiting",
            created_at=datetime.utcnow(),
            created_by=uuid4(),
        )

        json_dict = category.model_dump(mode='json')

        assert "org_id" in json_dict
        assert "name_normalized" in json_dict
        assert "created_at" in json_dict
        assert "created_by" in json_dict

        # No camelCase
        assert "orgId" not in json_dict
        assert "nameNormalized" not in json_dict
        assert "createdAt" not in json_dict
        assert "createdBy" not in json_dict

    def test_health_event_photo_response_snake_case_keys(self):
        """Health event photo responses must use snake_case."""
        from app.schemas.health import HealthEventPhotoResponse

        photo = HealthEventPhotoResponse(
            id=uuid4(),
            photo_url="https://example.com/photo.jpg",
            sort_order=0,
            created_at=datetime.utcnow(),
        )

        json_dict = photo.model_dump(mode='json')

        assert "photo_url" in json_dict
        assert "sort_order" in json_dict
        assert "created_at" in json_dict

        # No camelCase
        assert "photoUrl" not in json_dict
        assert "sortOrder" not in json_dict
        assert "createdAt" not in json_dict

    def test_health_event_response_photos_array(self):
        """
        iOS expects photos as an array (even if empty).

        iOS struct (HealthModels.swift):
        struct HealthEvent: Codable {
            let photos: [HealthEventPhoto]  // Array, not optional
        }
        """
        from app.schemas.health import HealthEventResponse, HealthEventPhotoResponse

        # Event with no photos - should have empty array
        event = HealthEventResponse(
            id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.utcnow(),
            notes=None,
            photos=[],  # Empty array
            created_at=datetime.utcnow(),
        )

        json_dict = event.model_dump(mode='json')

        assert "photos" in json_dict
        assert isinstance(json_dict["photos"], list)
        assert len(json_dict["photos"]) == 0

        # Event with photos
        event_with_photos = HealthEventResponse(
            id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.utcnow(),
            notes="Test notes",
            photos=[
                HealthEventPhotoResponse(
                    id=uuid4(),
                    photo_url="https://example.com/1.jpg",
                    sort_order=0,
                    created_at=datetime.utcnow(),
                ),
                HealthEventPhotoResponse(
                    id=uuid4(),
                    photo_url="https://example.com/2.jpg",
                    sort_order=1,
                    created_at=datetime.utcnow(),
                ),
            ],
            created_at=datetime.utcnow(),
        )

        json_dict_with_photos = event_with_photos.model_dump(mode='json')
        assert len(json_dict_with_photos["photos"]) == 2

    def test_health_event_nested_snake_case_keys(self):
        """Health event nested responses must use snake_case."""
        from app.schemas.health import HealthEventNested

        event = HealthEventNested(
            id=uuid4(),
            pet_id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.utcnow(),
            notes="Test notes",
            photos=[],
            created_at=datetime.utcnow(),
            created_by=uuid4(),
        )

        json_dict = event.model_dump(mode='json')

        assert "pet_id" in json_dict
        assert "category_id" in json_dict
        assert "occurred_at" in json_dict
        assert "created_at" in json_dict
        assert "created_by" in json_dict

        # No camelCase
        assert "petId" not in json_dict
        assert "categoryId" not in json_dict
        assert "occurredAt" not in json_dict

    def test_health_event_dates_are_iso8601(self):
        """Health event dates must be ISO8601 format for iOS."""
        from app.schemas.health import HealthEventResponse

        event = HealthEventResponse(
            id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime(2024, 6, 15, 14, 30, 0),
            notes=None,
            photos=[],
            created_at=datetime(2024, 6, 15, 10, 0, 0),
        )

        json_dict = event.model_dump(mode='json')

        # Dates should be strings
        assert isinstance(json_dict["occurred_at"], str)
        assert isinstance(json_dict["created_at"], str)

        # Should be ISO8601 parseable
        try:
            parsed = datetime.fromisoformat(
                json_dict["occurred_at"].replace('Z', '+00:00')
            )
            assert parsed is not None
        except ValueError:
            pytest.fail("occurred_at is not ISO8601 format")


class TestFoodContract:
    """Contract tests for food schemas - ensures iOS app compatibility."""

    def test_food_category_enum_matches_ios(self):
        """
        iOS FoodCategory enum must match backend.

        iOS enum (FoodModels.swift):
        enum FoodCategory: String, Codable {
            case dry = "dry"
            case wet = "wet"
            case snack = "snack"
        }
        """
        from app.models.food import FoodCategory

        expected_ios_values = {"dry", "wet", "snack"}
        actual_backend_values = {e.value for e in FoodCategory}

        assert actual_backend_values == expected_ios_values, \
            f"FoodCategory enum mismatch! " \
            f"Missing: {expected_ios_values - actual_backend_values}, " \
            f"Extra: {actual_backend_values - expected_ios_values}"

    def test_container_unit_enum_matches_ios(self):
        """
        iOS ContainerUnit enum must match backend.

        iOS enum (FoodModels.swift):
        enum ContainerUnit: String, Codable {
            case grams = "g"
            case ounces = "oz"
            case kilograms = "kg"
            case pounds = "lb"
        }
        """
        from app.models.food import ContainerUnit

        expected_ios_values = {"g", "oz", "kg", "lb"}
        actual_backend_values = {e.value for e in ContainerUnit}

        assert actual_backend_values == expected_ios_values, \
            f"ContainerUnit enum mismatch! " \
            f"Missing: {expected_ios_values - actual_backend_values}, " \
            f"Extra: {actual_backend_values - expected_ios_values}"

    def test_food_response_snake_case_keys(self):
        """Food responses must use snake_case."""
        from app.schemas.food import FoodResponse, FoodCategory, ContainerUnit

        food = FoodResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Dry Food",
            category=FoodCategory.DRY,
            calories_per_kg=3500.0,
            container_size=5.0,
            container_size_unit=ContainerUnit.KILOGRAMS,
            image_url="https://example.com/food.jpg",
            is_archived=False,
            created_at=datetime.utcnow(),
        )

        json_dict = food.model_dump(mode='json')

        assert "org_id" in json_dict
        assert "calories_per_kg" in json_dict
        assert "container_size" in json_dict
        assert "container_size_unit" in json_dict
        assert "image_url" in json_dict
        assert "is_archived" in json_dict
        assert "created_at" in json_dict

        # No camelCase
        assert "orgId" not in json_dict
        assert "caloriesPerKg" not in json_dict
        assert "containerSize" not in json_dict
        assert "containerSizeUnit" not in json_dict
        assert "imageUrl" not in json_dict
        assert "isArchived" not in json_dict
        assert "createdAt" not in json_dict

    def test_food_response_enum_values_are_strings(self):
        """
        iOS expects enum raw values (strings), not enum objects.

        iOS decodes:
        - category: "dry" ✅
        - category: {"dry": "dry"} ❌
        """
        from app.schemas.food import FoodResponse, FoodCategory, ContainerUnit

        food = FoodResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Wet Food",
            category=FoodCategory.WET,
            calories_per_kg=1200.0,
            container_size=400.0,
            container_size_unit=ContainerUnit.GRAMS,
            is_archived=False,
            created_at=datetime.utcnow(),
        )

        json_dict = food.model_dump(mode='json')

        # Enum values should be strings
        assert isinstance(json_dict["category"], str)
        assert json_dict["category"] == "wet"

        assert isinstance(json_dict["container_size_unit"], str)
        assert json_dict["container_size_unit"] == "g"


class TestFeedingContract:
    """Contract tests for feeding schemas - ensures iOS app compatibility."""

    def test_feeding_response_snake_case_keys(self):
        """Feeding responses must use snake_case."""
        from app.schemas.food import FeedingResponse, ContainerUnit

        feeding = FeedingResponse(
            id=uuid4(),
            pet_id=uuid4(),
            food_id=uuid4(),
            fed_by=uuid4(),
            fed_at=datetime.utcnow(),
            amount=100.0,
            amount_unit=ContainerUnit.GRAMS,
            calories=350.0,
            notes="Morning feeding",
            created_at=datetime.utcnow(),
        )

        json_dict = feeding.model_dump(mode='json')

        assert "pet_id" in json_dict
        assert "food_id" in json_dict
        assert "fed_by" in json_dict
        assert "fed_at" in json_dict
        assert "amount_unit" in json_dict
        assert "created_at" in json_dict

        # No camelCase
        assert "petId" not in json_dict
        assert "foodId" not in json_dict
        assert "fedBy" not in json_dict
        assert "fedAt" not in json_dict
        assert "amountUnit" not in json_dict
        assert "createdAt" not in json_dict

    def test_feeding_list_response_has_total_fields(self):
        """
        iOS FeedingListResponse expects total_calories and total count.

        iOS struct (FeedingModels.swift):
        struct FeedingListResponse: Codable {
            let feedings: [Feeding]
            let totalCalories: Float
            let total: Int
        }
        """
        from app.schemas.food import FeedingListResponse

        response = FeedingListResponse(
            feedings=[],
            total_calories=0.0,
            total=0,
        )

        json_dict = response.model_dump(mode='json')

        assert "feedings" in json_dict
        assert "total_calories" in json_dict
        assert "total" in json_dict
        assert isinstance(json_dict["feedings"], list)

        # No camelCase
        assert "totalCalories" not in json_dict

    def test_calorie_goal_response_snake_case_keys(self):
        """Calorie goal responses must use snake_case."""
        from app.schemas.food import CalorieGoalResponse

        goal = CalorieGoalResponse(
            id=uuid4(),
            pet_id=uuid4(),
            daily_calories=1200.0,
            effective_from=datetime.utcnow(),
            effective_until=None,
            notes="Winter goal",
            created_at=datetime.utcnow(),
        )

        json_dict = goal.model_dump(mode='json')

        assert "pet_id" in json_dict
        assert "daily_calories" in json_dict
        assert "effective_from" in json_dict
        assert "effective_until" in json_dict
        assert "created_at" in json_dict

        # No camelCase
        assert "petId" not in json_dict
        assert "dailyCalories" not in json_dict
        assert "effectiveFrom" not in json_dict
        assert "effectiveUntil" not in json_dict
        assert "createdAt" not in json_dict

    def test_calorie_goal_optional_fields_can_be_null(self):
        """
        iOS CalorieGoal has optional fields.

        iOS struct:
        struct CalorieGoal: Codable {
            let effectiveUntil: Date?  // Optional
            let notes: String?          // Optional
        }
        """
        from app.schemas.food import CalorieGoalResponse

        goal = CalorieGoalResponse(
            id=uuid4(),
            pet_id=uuid4(),
            daily_calories=1200.0,
            effective_from=datetime.utcnow(),
            effective_until=None,
            notes=None,
            created_at=datetime.utcnow(),
        )

        json_dict = goal.model_dump(mode='json')

        assert json_dict["effective_until"] is None
        assert json_dict["notes"] is None


class TestAuthContract:
    """Contract tests for auth response schemas - ensures iOS app compatibility."""

    def test_auth_token_format_is_string(self):
        """
        iOS expects JWT token as plain string.

        iOS struct (AuthModels.swift):
        struct AuthResponse: Codable {
            let token: String  // NOT an object, just a string
        }
        """
        from app.api.endpoints.auth import AuthResponse, UserResponse

        auth = AuthResponse(
            token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            user=UserResponse(
                id=str(uuid4()),
                email="test@example.com",
                first_name="Test",
                last_name="User",
            ),
            families=[],
        )

        json_dict = auth.model_dump(mode='json')

        assert isinstance(json_dict["token"], str)
        assert len(json_dict["token"]) > 0

    def test_families_array_can_be_empty(self):
        """
        iOS handles empty families array (new user case).

        iOS struct:
        struct AuthResponse: Codable {
            let families: [Family]  // Can be empty []
        }
        """
        from app.api.endpoints.auth import AuthResponse, UserResponse

        auth = AuthResponse(
            token="test-token",
            user=UserResponse(
                id=str(uuid4()),
                email="test@example.com",
                first_name="Test",
                last_name=None,
            ),
            families=[],  # Empty array
        )

        json_dict = auth.model_dump(mode='json')

        assert "families" in json_dict
        assert isinstance(json_dict["families"], list)
        assert len(json_dict["families"]) == 0

    def test_delete_account_response_has_required_fields(self):
        """
        iOS DeleteAccountResponse expects success and steps_completed.

        iOS struct (AuthModels.swift):
        struct DeleteAccountResponse: Codable {
            let success: Bool
            let stepsCompleted: [String]
        }
        """
        from app.api.endpoints.auth import DeleteAccountResponse

        response = DeleteAccountResponse(
            success=True,
            steps_completed=["deleted_device_tokens", "deleted_account"],
        )

        json_dict = response.model_dump(mode='json')

        assert "success" in json_dict
        assert "steps_completed" in json_dict
        assert isinstance(json_dict["success"], bool)
        assert isinstance(json_dict["steps_completed"], list)

        # No camelCase
        assert "stepsCompleted" not in json_dict


class TestResponseCodeContracts:
    """Test that HTTP status codes match iOS app expectations."""

    def test_status_code_expectations(self):
        """
        Document expected HTTP status codes that iOS app handles.

        iOS app expects:
        - 200: Success
        - 201: Created
        - 204: No Content
        - 400: Bad Request (validation error)
        - 401: Unauthorized (missing/invalid token)
        - 403: Forbidden (no access to resource)
        - 404: Not Found
        - 422: Unprocessable Entity (Pydantic validation)
        - 429: Too Many Requests (rate limit)
        - 500: Internal Server Error
        - 503: Service Unavailable

        Changing status codes for existing endpoints will break error handling.
        """
        expected_status_codes = {200, 201, 204, 400, 401, 403, 404, 422, 429, 500, 503}

        # This is a documentation test - no actual assertion
        # Just validates that we're aware of the contract
        assert len(expected_status_codes) > 0
