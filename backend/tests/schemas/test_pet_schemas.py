"""
Tests for Pet Pydantic schemas.

Validates pet schema behavior to prevent breaking changes to iOS app.
"""
from datetime import datetime, date, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.pet import (
    PetCreate,
    PetUpdate,
    PetResponse,
    PetListResponse,
    HealthRecordCreate,
    HealthRecordResponse,
    parse_date_flexible,
)


class TestParseDateFlexible:
    """Tests for the parse_date_flexible helper function."""

    def test_parse_date_from_date_object(self):
        """Should return date object as-is."""
        test_date = date(2024, 3, 15)
        result = parse_date_flexible(test_date)
        assert result == test_date
        assert isinstance(result, date)

    def test_parse_date_from_datetime_object(self):
        """Should extract date from datetime object."""
        test_datetime = datetime(2024, 3, 15, 14, 30, 0)
        result = parse_date_flexible(test_datetime)
        assert result == date(2024, 3, 15)
        assert isinstance(result, date)
        assert not isinstance(result, datetime)

    def test_parse_date_from_iso_string(self):
        """Should parse ISO date string (YYYY-MM-DD)."""
        result = parse_date_flexible("2024-03-15")
        assert result == date(2024, 3, 15)

    def test_parse_date_from_datetime_string(self):
        """Should parse datetime ISO string and extract date."""
        result = parse_date_flexible("2024-03-15T14:30:00")
        assert result == date(2024, 3, 15)

    def test_parse_date_from_datetime_string_with_z_suffix(self):
        """Should parse datetime string with Z timezone suffix."""
        result = parse_date_flexible("2024-03-15T14:30:00Z")
        assert result == date(2024, 3, 15)

    def test_parse_date_from_datetime_string_with_timezone(self):
        """Should parse datetime string with timezone offset."""
        result = parse_date_flexible("2024-03-15T14:30:00+00:00")
        assert result == date(2024, 3, 15)

    def test_parse_date_none_returns_none(self):
        """Should return None when value is None."""
        result = parse_date_flexible(None)
        assert result is None

    def test_parse_date_invalid_string_raises_error(self):
        """Should raise ValueError for invalid date string."""
        with pytest.raises(ValueError, match="Cannot parse date from"):
            parse_date_flexible("invalid-date")

    def test_parse_date_invalid_type_raises_error(self):
        """Should raise ValueError for invalid type."""
        with pytest.raises(ValueError, match="Cannot parse date from"):
            parse_date_flexible(12345)

    def test_parse_date_partial_datetime_string(self):
        """Should handle partial datetime strings by extracting date portion."""
        result = parse_date_flexible("2024-03-15T14:30:00.123456")
        assert result == date(2024, 3, 15)


class TestPetCreate:
    """Tests for PetCreate schema."""

    def test_pet_create_required_fields_only(self):
        """Should create pet with only required fields."""
        pet = PetCreate(
            name="Orest",
            kind="dog",
        )

        assert pet.name == "Orest"
        assert pet.kind == "dog"
        assert pet.photo_url is None
        assert pet.current_weight is None
        assert pet.date_of_birth is None

    def test_pet_create_with_all_fields(self):
        """Should create pet with all optional fields."""
        dob = date(2020, 5, 10)

        pet = PetCreate(
            name="Orest",
            kind="dog",
            photo_url="https://example.com/orest.jpg",
            current_weight=15.5,
            date_of_birth=dob,
        )

        assert pet.name == "Orest"
        assert pet.kind == "dog"
        assert pet.photo_url == "https://example.com/orest.jpg"
        assert pet.current_weight == 15.5
        assert pet.date_of_birth == dob

    def test_pet_create_missing_name_raises_error(self):
        """Should raise ValidationError when name is missing."""
        with pytest.raises(ValidationError) as exc_info:
            PetCreate(kind="dog")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_pet_create_missing_kind_raises_error(self):
        """Should raise ValidationError when kind is missing."""
        with pytest.raises(ValidationError) as exc_info:
            PetCreate(name="Orest")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("kind",) for e in errors)

    def test_pet_create_weight_accepts_integer(self):
        """Should accept integer weight and convert to float."""
        pet = PetCreate(name="Orest", kind="dog", current_weight=15)
        assert pet.current_weight == 15.0
        assert isinstance(pet.current_weight, float)

    def test_pet_create_weight_accepts_float(self):
        """Should accept float weight."""
        pet = PetCreate(name="Orest", kind="dog", current_weight=15.75)
        assert pet.current_weight == 15.75

    def test_pet_create_weight_zero_is_valid(self):
        """Should accept zero weight (e.g., newborn)."""
        pet = PetCreate(name="Orest", kind="dog", current_weight=0.0)
        assert pet.current_weight == 0.0

    def test_pet_create_weight_negative_is_valid(self):
        """Schema does not validate weight range, so negative is technically accepted."""
        # Note: Business logic validation should happen at service layer
        pet = PetCreate(name="Orest", kind="dog", current_weight=-5.0)
        assert pet.current_weight == -5.0

    def test_pet_create_weight_very_large_is_valid(self):
        """Should accept very large weight values."""
        pet = PetCreate(name="Orest", kind="dog", current_weight=999.99)
        assert pet.current_weight == 999.99

    def test_pet_create_date_of_birth_as_date_object(self):
        """Should accept date object for date_of_birth."""
        dob = date(2020, 5, 10)
        pet = PetCreate(name="Orest", kind="dog", date_of_birth=dob)
        assert pet.date_of_birth == dob

    def test_pet_create_date_of_birth_as_iso_string(self):
        """Should parse ISO date string for date_of_birth."""
        pet = PetCreate(name="Orest", kind="dog", date_of_birth="2020-05-10")
        assert pet.date_of_birth == date(2020, 5, 10)

    def test_pet_create_date_of_birth_as_datetime_string(self):
        """Should parse datetime string and extract date for date_of_birth."""
        pet = PetCreate(name="Orest", kind="dog", date_of_birth="2020-05-10T14:30:00Z")
        assert pet.date_of_birth == date(2020, 5, 10)

    def test_pet_create_date_of_birth_invalid_string_raises_error(self):
        """Should raise ValidationError for invalid date string."""
        with pytest.raises(ValidationError) as exc_info:
            PetCreate(name="Orest", kind="dog", date_of_birth="invalid-date")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("date_of_birth",) for e in errors)

    def test_pet_create_kind_accepts_any_string(self):
        """Kind field accepts any string value (no enum validation)."""
        valid_kinds = ["dog", "cat", "bird", "rabbit", "hamster", "other", "Dog", "DOG"]
        for kind in valid_kinds:
            pet = PetCreate(name="Pet", kind=kind)
            assert pet.kind == kind

    def test_pet_create_empty_string_name_is_valid(self):
        """Schema allows empty string name (business logic should validate)."""
        pet = PetCreate(name="", kind="dog")
        assert pet.name == ""

    def test_pet_create_empty_string_kind_is_valid(self):
        """Schema allows empty string kind (business logic should validate)."""
        pet = PetCreate(name="Orest", kind="")
        assert pet.kind == ""

    def test_pet_create_very_long_name(self):
        """Should accept very long name strings."""
        long_name = "O" * 1000
        pet = PetCreate(name=long_name, kind="dog")
        assert pet.name == long_name
        assert len(pet.name) == 1000

    def test_pet_create_special_characters_in_name(self):
        """Should accept special characters in name."""
        special_names = ["O'Rest", "Orest-Junior", "Orest (Jr.)", "Остов", "オレスト"]
        for name in special_names:
            pet = PetCreate(name=name, kind="dog")
            assert pet.name == name

    def test_pet_create_photo_url_with_valid_url(self):
        """Should accept valid photo URLs."""
        urls = [
            "https://example.com/photo.jpg",
            "http://example.com/photo.png",
            "https://cdn.example.com/photos/abc123.jpg?size=large",
        ]
        for url in urls:
            pet = PetCreate(name="Orest", kind="dog", photo_url=url)
            assert pet.photo_url == url

    def test_pet_create_photo_url_with_empty_string(self):
        """Should accept empty string photo_url (schema doesn't validate URL format)."""
        pet = PetCreate(name="Orest", kind="dog", photo_url="")
        assert pet.photo_url == ""


class TestPetUpdate:
    """Tests for PetUpdate schema."""

    def test_pet_update_all_fields_optional(self):
        """All fields in update schema should be optional."""
        update = PetUpdate()

        assert update.name is None
        assert update.kind is None
        assert update.photo_url is None
        assert update.current_weight is None
        assert update.date_of_birth is None

    def test_pet_update_single_field_name(self):
        """Should allow updating only name."""
        update = PetUpdate(name="Updated Name")

        assert update.name == "Updated Name"
        assert update.kind is None
        assert update.current_weight is None

    def test_pet_update_single_field_kind(self):
        """Should allow updating only kind."""
        update = PetUpdate(kind="cat")

        assert update.kind == "cat"
        assert update.name is None

    def test_pet_update_single_field_weight(self):
        """Should allow updating only weight."""
        update = PetUpdate(current_weight=20.5)

        assert update.current_weight == 20.5
        assert update.name is None

    def test_pet_update_single_field_photo_url(self):
        """Should allow updating only photo_url."""
        update = PetUpdate(photo_url="https://example.com/new.jpg")

        assert update.photo_url == "https://example.com/new.jpg"
        assert update.name is None

    def test_pet_update_single_field_date_of_birth(self):
        """Should allow updating only date_of_birth."""
        dob = date(2021, 6, 15)
        update = PetUpdate(date_of_birth=dob)

        assert update.date_of_birth == dob
        assert update.name is None

    def test_pet_update_multiple_fields(self):
        """Should allow updating multiple fields."""
        update = PetUpdate(
            name="Updated Pet",
            kind="cat",
            current_weight=12.3,
        )

        assert update.name == "Updated Pet"
        assert update.kind == "cat"
        assert update.current_weight == 12.3
        assert update.photo_url is None

    def test_pet_update_all_fields(self):
        """Should allow updating all fields."""
        dob = date(2019, 3, 20)

        update = PetUpdate(
            name="Fully Updated",
            kind="bird",
            photo_url="https://example.com/bird.jpg",
            current_weight=0.5,
            date_of_birth=dob,
        )

        assert update.name == "Fully Updated"
        assert update.kind == "bird"
        assert update.photo_url == "https://example.com/bird.jpg"
        assert update.current_weight == 0.5
        assert update.date_of_birth == dob

    def test_pet_update_date_of_birth_as_string(self):
        """Should parse date string for date_of_birth."""
        update = PetUpdate(date_of_birth="2019-03-20")
        assert update.date_of_birth == date(2019, 3, 20)

    def test_pet_update_date_of_birth_as_datetime_string(self):
        """Should parse datetime string for date_of_birth."""
        update = PetUpdate(date_of_birth="2019-03-20T10:00:00Z")
        assert update.date_of_birth == date(2019, 3, 20)

    def test_pet_update_date_of_birth_invalid_raises_error(self):
        """Should raise ValidationError for invalid date."""
        with pytest.raises(ValidationError) as exc_info:
            PetUpdate(date_of_birth="not-a-date")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("date_of_birth",) for e in errors)

    def test_pet_update_weight_type_validation(self):
        """Should validate weight type."""
        with pytest.raises(ValidationError) as exc_info:
            PetUpdate(current_weight="not-a-number")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("current_weight",) for e in errors)


class TestPetResponse:
    """Tests for PetResponse schema."""

    def test_pet_response_required_fields(self):
        """Response should require all non-nullable fields."""
        now = datetime.utcnow()

        response = PetResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Orest",
            kind="dog",
            created_at=now,
        )

        assert response.id is not None
        assert response.org_id is not None
        assert response.name == "Orest"
        assert response.kind == "dog"
        assert response.created_at == now

    def test_pet_response_optional_fields_default_to_none(self):
        """Optional fields should default to None."""
        response = PetResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Orest",
            kind="dog",
            created_at=datetime.utcnow(),
        )

        assert response.photo_url is None
        assert response.current_weight is None
        assert response.date_of_birth is None
        assert response.created_by is None

    def test_pet_response_with_all_fields(self):
        """Response should accept all fields."""
        now = datetime.utcnow()
        dob = date(2020, 5, 10)
        pet_id = uuid4()
        org_id = uuid4()
        user_id = uuid4()

        response = PetResponse(
            id=pet_id,
            org_id=org_id,
            name="Orest",
            kind="dog",
            photo_url="https://example.com/orest.jpg",
            current_weight=15.5,
            date_of_birth=dob,
            created_at=now,
            created_by=user_id,
        )

        assert response.id == pet_id
        assert response.org_id == org_id
        assert response.name == "Orest"
        assert response.kind == "dog"
        assert response.photo_url == "https://example.com/orest.jpg"
        assert response.current_weight == 15.5
        assert response.date_of_birth == dob
        assert response.created_at == now
        assert response.created_by == user_id

    def test_pet_response_from_attributes_config(self):
        """Response should have from_attributes=True for ORM models."""
        # The model_config should allow creation from ORM objects
        assert PetResponse.model_config.get("from_attributes") is True

    def test_pet_response_id_must_be_uuid(self):
        """ID field must be a valid UUID."""
        with pytest.raises(ValidationError) as exc_info:
            PetResponse(
                id="not-a-uuid",
                org_id=uuid4(),
                name="Orest",
                kind="dog",
                created_at=datetime.utcnow(),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)

    def test_pet_response_org_id_must_be_uuid(self):
        """Org ID field must be a valid UUID."""
        with pytest.raises(ValidationError) as exc_info:
            PetResponse(
                id=uuid4(),
                org_id="not-a-uuid",
                name="Orest",
                kind="dog",
                created_at=datetime.utcnow(),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("org_id",) for e in errors)

    def test_pet_response_created_at_must_be_datetime(self):
        """Created_at must be a datetime object."""
        with pytest.raises(ValidationError) as exc_info:
            PetResponse(
                id=uuid4(),
                org_id=uuid4(),
                name="Orest",
                kind="dog",
                created_at="not-a-datetime",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("created_at",) for e in errors)

    def test_pet_response_weight_must_be_numeric(self):
        """Current weight must be numeric."""
        with pytest.raises(ValidationError) as exc_info:
            PetResponse(
                id=uuid4(),
                org_id=uuid4(),
                name="Orest",
                kind="dog",
                created_at=datetime.utcnow(),
                current_weight="heavy",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("current_weight",) for e in errors)

    def test_pet_response_accepts_uuid_strings(self):
        """Response should accept UUID strings and convert them."""
        pet_id = uuid4()
        org_id = uuid4()

        response = PetResponse(
            id=str(pet_id),
            org_id=str(org_id),
            name="Orest",
            kind="dog",
            created_at=datetime.utcnow(),
        )

        assert response.id == pet_id
        assert response.org_id == org_id


class TestPetListResponse:
    """Tests for PetListResponse schema."""

    def test_pet_list_response_empty_list(self):
        """Should accept empty list of pets."""
        response = PetListResponse(pets=[])
        assert response.pets == []
        assert len(response.pets) == 0

    def test_pet_list_response_single_pet(self):
        """Should accept list with single pet."""
        pet = PetResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Orest",
            kind="dog",
            created_at=datetime.utcnow(),
        )

        response = PetListResponse(pets=[pet])
        assert len(response.pets) == 1
        assert response.pets[0].name == "Orest"

    def test_pet_list_response_multiple_pets(self):
        """Should accept list with multiple pets."""
        org_id = uuid4()
        now = datetime.utcnow()

        pets = [
            PetResponse(
                id=uuid4(),
                org_id=org_id,
                name="Orest",
                kind="dog",
                created_at=now,
            ),
            PetResponse(
                id=uuid4(),
                org_id=org_id,
                name="Whiskers",
                kind="cat",
                created_at=now,
            ),
            PetResponse(
                id=uuid4(),
                org_id=org_id,
                name="Tweety",
                kind="bird",
                created_at=now,
            ),
        ]

        response = PetListResponse(pets=pets)
        assert len(response.pets) == 3
        assert response.pets[0].name == "Orest"
        assert response.pets[1].name == "Whiskers"
        assert response.pets[2].name == "Tweety"

    def test_pet_list_response_preserves_order(self):
        """Should preserve order of pets in list."""
        org_id = uuid4()
        now = datetime.utcnow()

        pets = [
            PetResponse(id=uuid4(), org_id=org_id, name=f"Pet{i}", kind="dog", created_at=now)
            for i in range(10)
        ]

        response = PetListResponse(pets=pets)
        for i in range(10):
            assert response.pets[i].name == f"Pet{i}"


class TestHealthRecordCreate:
    """Tests for HealthRecordCreate schema."""

    def test_health_record_create_all_fields_optional(self):
        """All fields should be optional."""
        record = HealthRecordCreate()

        assert record.age_years is None
        assert record.weight_pounds is None
        assert record.notes is None

    def test_health_record_create_with_age_only(self):
        """Should accept only age_years."""
        record = HealthRecordCreate(age_years=5.5)

        assert record.age_years == 5.5
        assert record.weight_pounds is None
        assert record.notes is None

    def test_health_record_create_with_weight_only(self):
        """Should accept only weight_pounds."""
        record = HealthRecordCreate(weight_pounds=15.7)

        assert record.weight_pounds == 15.7
        assert record.age_years is None
        assert record.notes is None

    def test_health_record_create_with_notes_only(self):
        """Should accept only notes."""
        record = HealthRecordCreate(notes="Annual checkup")

        assert record.notes == "Annual checkup"
        assert record.age_years is None
        assert record.weight_pounds is None

    def test_health_record_create_with_all_fields(self):
        """Should accept all fields."""
        record = HealthRecordCreate(
            age_years=3.5,
            weight_pounds=45.2,
            notes="Healthy condition, all vaccines up to date",
        )

        assert record.age_years == 3.5
        assert record.weight_pounds == 45.2
        assert record.notes == "Healthy condition, all vaccines up to date"

    def test_health_record_create_age_accepts_integer(self):
        """Should accept integer age and convert to float."""
        record = HealthRecordCreate(age_years=5)
        assert record.age_years == 5.0
        assert isinstance(record.age_years, float)

    def test_health_record_create_age_accepts_float(self):
        """Should accept float age."""
        record = HealthRecordCreate(age_years=5.75)
        assert record.age_years == 5.75

    def test_health_record_create_age_zero_is_valid(self):
        """Should accept zero age (e.g., newborn)."""
        record = HealthRecordCreate(age_years=0.0)
        assert record.age_years == 0.0

    def test_health_record_create_weight_accepts_integer(self):
        """Should accept integer weight and convert to float."""
        record = HealthRecordCreate(weight_pounds=50)
        assert record.weight_pounds == 50.0
        assert isinstance(record.weight_pounds, float)

    def test_health_record_create_weight_accepts_float(self):
        """Should accept float weight."""
        record = HealthRecordCreate(weight_pounds=45.25)
        assert record.weight_pounds == 45.25

    def test_health_record_create_weight_zero_is_valid(self):
        """Should accept zero weight."""
        record = HealthRecordCreate(weight_pounds=0.0)
        assert record.weight_pounds == 0.0

    def test_health_record_create_age_invalid_type_raises_error(self):
        """Should raise ValidationError for invalid age type."""
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordCreate(age_years="five years")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("age_years",) for e in errors)

    def test_health_record_create_weight_invalid_type_raises_error(self):
        """Should raise ValidationError for invalid weight type."""
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordCreate(weight_pounds="fifty pounds")

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("weight_pounds",) for e in errors)

    def test_health_record_create_notes_empty_string_is_valid(self):
        """Should accept empty string notes."""
        record = HealthRecordCreate(notes="")
        assert record.notes == ""

    def test_health_record_create_notes_long_text(self):
        """Should accept long text in notes."""
        long_notes = "A" * 5000
        record = HealthRecordCreate(notes=long_notes)
        assert len(record.notes) == 5000

    def test_health_record_create_notes_special_characters(self):
        """Should accept special characters in notes."""
        special_notes = "Weight: 45.2lbs\nAge: 3½ years\nVet: Dr. O'Brien\n✓ Healthy"
        record = HealthRecordCreate(notes=special_notes)
        assert record.notes == special_notes


class TestHealthRecordResponse:
    """Tests for HealthRecordResponse schema."""

    def test_health_record_response_required_fields(self):
        """Response should require all non-nullable fields."""
        now = datetime.utcnow()
        record_id = uuid4()
        pet_id = uuid4()

        response = HealthRecordResponse(
            id=record_id,
            pet_id=pet_id,
            recorded_at=now,
        )

        assert response.id == record_id
        assert response.pet_id == pet_id
        assert response.recorded_at == now

    def test_health_record_response_optional_fields_default_to_none(self):
        """Optional fields should default to None."""
        response = HealthRecordResponse(
            id=uuid4(),
            pet_id=uuid4(),
            recorded_at=datetime.utcnow(),
        )

        assert response.age_years is None
        assert response.weight_pounds is None
        assert response.notes is None

    def test_health_record_response_with_all_fields(self):
        """Response should accept all fields."""
        now = datetime.utcnow()
        record_id = uuid4()
        pet_id = uuid4()

        response = HealthRecordResponse(
            id=record_id,
            pet_id=pet_id,
            age_years=4.5,
            weight_pounds=50.3,
            notes="Regular checkup - all good",
            recorded_at=now,
        )

        assert response.id == record_id
        assert response.pet_id == pet_id
        assert response.age_years == 4.5
        assert response.weight_pounds == 50.3
        assert response.notes == "Regular checkup - all good"
        assert response.recorded_at == now

    def test_health_record_response_from_attributes_config(self):
        """Response should have from_attributes=True for ORM models."""
        assert HealthRecordResponse.model_config.get("from_attributes") is True

    def test_health_record_response_id_must_be_uuid(self):
        """ID field must be a valid UUID."""
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordResponse(
                id="not-a-uuid",
                pet_id=uuid4(),
                recorded_at=datetime.utcnow(),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("id",) for e in errors)

    def test_health_record_response_pet_id_must_be_uuid(self):
        """Pet ID field must be a valid UUID."""
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordResponse(
                id=uuid4(),
                pet_id="not-a-uuid",
                recorded_at=datetime.utcnow(),
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("pet_id",) for e in errors)

    def test_health_record_response_recorded_at_must_be_datetime(self):
        """Recorded_at must be a datetime object."""
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordResponse(
                id=uuid4(),
                pet_id=uuid4(),
                recorded_at="not-a-datetime",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("recorded_at",) for e in errors)

    def test_health_record_response_accepts_uuid_strings(self):
        """Response should accept UUID strings and convert them."""
        record_id = uuid4()
        pet_id = uuid4()

        response = HealthRecordResponse(
            id=str(record_id),
            pet_id=str(pet_id),
            recorded_at=datetime.utcnow(),
        )

        assert response.id == record_id
        assert response.pet_id == pet_id

    def test_health_record_response_age_must_be_numeric(self):
        """Age must be numeric."""
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordResponse(
                id=uuid4(),
                pet_id=uuid4(),
                recorded_at=datetime.utcnow(),
                age_years="five",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("age_years",) for e in errors)

    def test_health_record_response_weight_must_be_numeric(self):
        """Weight must be numeric."""
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordResponse(
                id=uuid4(),
                pet_id=uuid4(),
                recorded_at=datetime.utcnow(),
                weight_pounds="fifty",
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("weight_pounds",) for e in errors)


class TestBoundaryValues:
    """Tests for boundary and edge case values."""

    def test_pet_create_date_of_birth_future_date(self):
        """Should accept future date (validation should happen at service layer)."""
        future_date = date.today() + timedelta(days=365)
        pet = PetCreate(name="Future Pet", kind="dog", date_of_birth=future_date)
        assert pet.date_of_birth == future_date

    def test_pet_create_date_of_birth_very_old_date(self):
        """Should accept very old dates."""
        old_date = date(1900, 1, 1)
        pet = PetCreate(name="Ancient Pet", kind="dog", date_of_birth=old_date)
        assert pet.date_of_birth == old_date

    def test_health_record_large_age_values(self):
        """Should accept large age values."""
        record = HealthRecordCreate(age_years=999.99)
        assert record.age_years == 999.99

    def test_health_record_large_weight_values(self):
        """Should accept large weight values."""
        record = HealthRecordCreate(weight_pounds=9999.99)
        assert record.weight_pounds == 9999.99

    def test_health_record_fractional_age(self):
        """Should accept fractional age values for precision."""
        record = HealthRecordCreate(age_years=2.333333)
        assert record.age_years == 2.333333

    def test_health_record_fractional_weight(self):
        """Should accept fractional weight values for precision."""
        record = HealthRecordCreate(weight_pounds=15.123456)
        assert record.weight_pounds == 15.123456

    def test_pet_response_created_at_with_timezone(self):
        """Should handle datetime with timezone information."""
        # UTC datetime
        now_utc = datetime.utcnow()
        response = PetResponse(
            id=uuid4(),
            org_id=uuid4(),
            name="Test",
            kind="dog",
            created_at=now_utc,
        )
        assert response.created_at == now_utc

    def test_parse_date_handles_leap_year(self):
        """Should correctly parse leap year dates."""
        leap_date = parse_date_flexible("2024-02-29")
        assert leap_date == date(2024, 2, 29)

    def test_parse_date_handles_year_boundaries(self):
        """Should correctly parse year boundary dates."""
        result = parse_date_flexible("2024-12-31")
        assert result == date(2024, 12, 31)

        result = parse_date_flexible("2024-01-01")
        assert result == date(2024, 1, 1)
