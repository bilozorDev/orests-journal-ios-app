"""
Tests for Health Event Pydantic schemas.

Validates health event schema behavior to prevent breaking changes to iOS app.
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.health import (
    HealthCategoryCreate,
    HealthCategoryResponse,
    HealthEventCreate,
    HealthEventUpdate,
    HealthEventResponse,
    HealthEventPhotoResponse,
    HealthEventNested,
    HealthEventWithCategory,
    HealthEventListResponse,
    HealthCategoryListResponse,
)


class TestHealthCategoryCreate:
    """Tests for HealthCategoryCreate schema."""

    def test_health_category_create_required_field(self):
        """Should create category with only required name field."""
        category = HealthCategoryCreate(name="Vaccination")

        assert category.name == "Vaccination"

    def test_health_category_create_with_whitespace(self):
        """Should accept category names with leading/trailing whitespace."""
        category = HealthCategoryCreate(name="  Allergy  ")

        # Schema doesn't strip whitespace - service layer handles normalization
        assert category.name == "  Allergy  "

    def test_health_category_create_empty_string_allowed(self):
        """Should allow empty string (validation happens in service layer)."""
        category = HealthCategoryCreate(name="")

        assert category.name == ""

    def test_health_category_create_special_characters(self):
        """Should accept category names with special characters."""
        special_names = [
            "Weight Check (Monthly)",
            "Skin Issue - Rash",
            "Dental: Cleaning",
            "Surgery/Post-Op",
        ]

        for name in special_names:
            category = HealthCategoryCreate(name=name)
            assert category.name == name

    def test_health_category_create_long_name(self):
        """Should accept long category names."""
        long_name = "A" * 255
        category = HealthCategoryCreate(name=long_name)

        assert category.name == long_name
        assert len(category.name) == 255


class TestHealthCategoryResponse:
    """Tests for HealthCategoryResponse schema."""

    def test_health_category_response_required_fields(self):
        """Response should require all non-nullable fields."""
        category = HealthCategoryResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Vaccination",
            name_normalized="vaccination",
            created_at=datetime.now(UTC),
        )

        assert category.id is not None
        assert category.family_id is not None
        assert category.name == "Vaccination"
        assert category.name_normalized == "vaccination"
        assert category.created_at is not None
        assert category.created_by is None  # Optional field

    def test_health_category_response_with_created_by(self):
        """Response should include created_by when provided."""
        user_id = uuid4()
        category = HealthCategoryResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Vaccination",
            name_normalized="vaccination",
            created_at=datetime.now(UTC),
            created_by=user_id,
        )

        assert category.created_by == user_id

    def test_health_category_response_from_attributes(self):
        """Response should support from_attributes for ORM models."""
        # Verify ConfigDict is set correctly
        assert HealthCategoryResponse.model_config["from_attributes"] is True

    def test_health_category_response_normalization_lowercase(self):
        """Name normalized should typically be lowercase version."""
        category = HealthCategoryResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Weight Check",
            name_normalized="weight check",
            created_at=datetime.now(UTC),
        )

        assert category.name == "Weight Check"
        assert category.name_normalized == "weight check"


class TestHealthEventCreate:
    """Tests for HealthEventCreate schema."""

    def test_health_event_create_minimal_fields(self):
        """Should create event with only required category_name."""
        event = HealthEventCreate(category_name="Vaccination")

        assert event.category_name == "Vaccination"
        assert event.occurred_at is None  # Defaults to None (server uses now)
        assert event.notes is None
        assert event.notify_family is False  # Default

    def test_health_event_create_with_all_fields(self):
        """Should create event with all optional fields."""
        occurred_time = datetime.now(UTC) - timedelta(hours=2)

        event = HealthEventCreate(
            category_name="Vaccination",
            occurred_at=occurred_time,
            notes="Annual rabies vaccination. No adverse reactions observed.",
            notify_family=True,
        )

        assert event.category_name == "Vaccination"
        assert event.occurred_at == occurred_time
        assert event.notes == "Annual rabies vaccination. No adverse reactions observed."
        assert event.notify_family is True

    def test_health_event_create_notify_family_default_false(self):
        """Notify family should default to False."""
        event = HealthEventCreate(category_name="Weight Check")

        assert event.notify_family is False

    def test_health_event_create_with_custom_timestamp(self):
        """Should accept custom occurred_at timestamp for backdating events."""
        past_time = datetime.now(UTC) - timedelta(days=7)

        event = HealthEventCreate(
            category_name="Vet Visit",
            occurred_at=past_time,
        )

        assert event.occurred_at == past_time

    def test_health_event_create_future_timestamp(self):
        """Should accept future timestamps (e.g., scheduled appointments)."""
        future_time = datetime.now(UTC) + timedelta(days=30)

        event = HealthEventCreate(
            category_name="Scheduled Checkup",
            occurred_at=future_time,
        )

        assert event.occurred_at == future_time

    def test_health_event_create_long_notes(self):
        """Should accept long notes text."""
        long_notes = "A" * 10000  # 10K characters

        event = HealthEventCreate(
            category_name="Surgery",
            notes=long_notes,
        )

        assert len(event.notes) == 10000

    def test_health_event_create_empty_notes(self):
        """Should accept empty string for notes."""
        event = HealthEventCreate(
            category_name="Weight Check",
            notes="",
        )

        assert event.notes == ""

    def test_health_event_create_multiline_notes(self):
        """Should accept notes with newlines and formatting."""
        multiline_notes = """Symptoms observed:
- Lethargy
- Loss of appetite
- Vomiting

Treatment plan:
1. Prescribed medication
2. Follow-up in 3 days"""

        event = HealthEventCreate(
            category_name="Illness",
            notes=multiline_notes,
        )

        assert "\n" in event.notes
        assert event.notes == multiline_notes


class TestHealthEventUpdate:
    """Tests for HealthEventUpdate schema."""

    def test_health_event_update_all_fields_optional(self):
        """All fields in update schema should be optional."""
        update = HealthEventUpdate()

        assert update.category_name is None
        assert update.occurred_at is None
        assert update.notes is None

    def test_health_event_update_single_field(self):
        """Should allow updating a single field."""
        update = HealthEventUpdate(category_name="Updated Category")

        assert update.category_name == "Updated Category"
        assert update.occurred_at is None  # Other fields remain None
        assert update.notes is None

    def test_health_event_update_multiple_fields(self):
        """Should allow updating multiple fields."""
        new_time = datetime.now(UTC) - timedelta(hours=1)

        update = HealthEventUpdate(
            category_name="Corrected Category",
            occurred_at=new_time,
            notes="Updated notes with more details",
        )

        assert update.category_name == "Corrected Category"
        assert update.occurred_at == new_time
        assert update.notes == "Updated notes with more details"

    def test_health_event_update_clear_notes(self):
        """Should allow explicitly clearing notes."""
        update = HealthEventUpdate(notes="")

        assert update.notes == ""

    def test_health_event_update_change_timestamp(self):
        """Should allow changing occurred_at timestamp."""
        corrected_time = datetime.now(UTC) - timedelta(days=1)

        update = HealthEventUpdate(occurred_at=corrected_time)

        assert update.occurred_at == corrected_time


class TestHealthEventPhotoResponse:
    """Tests for HealthEventPhotoResponse schema."""

    def test_health_event_photo_response_required_fields(self):
        """Response should require all fields."""
        photo = HealthEventPhotoResponse(
            id=uuid4(),
            photo_url="https://cdn.example.com/photos/abc123.jpg",
            sort_order=0,
            created_at=datetime.now(UTC),
        )

        assert photo.id is not None
        assert photo.photo_url == "https://cdn.example.com/photos/abc123.jpg"
        assert photo.sort_order == 0
        assert photo.created_at is not None

    def test_health_event_photo_response_sort_order_values(self):
        """Should accept various sort_order values."""
        for sort_order in [0, 1, 2, 5, 10]:
            photo = HealthEventPhotoResponse(
                id=uuid4(),
                photo_url="https://example.com/photo.jpg",
                sort_order=sort_order,
                created_at=datetime.now(UTC),
            )
            assert photo.sort_order == sort_order

    def test_health_event_photo_response_from_attributes(self):
        """Response should support from_attributes for ORM models."""
        assert HealthEventPhotoResponse.model_config["from_attributes"] is True

    def test_health_event_photo_response_url_formats(self):
        """Should accept various URL formats."""
        urls = [
            "https://cdn.example.com/photos/abc123.jpg",
            "https://r2.cloudflare.com/bucket/image.png",
            "https://storage.googleapis.com/bucket/path/to/file.webp",
        ]

        for url in urls:
            photo = HealthEventPhotoResponse(
                id=uuid4(),
                photo_url=url,
                sort_order=0,
                created_at=datetime.now(UTC),
            )
            assert photo.photo_url == url


class TestHealthEventResponse:
    """Tests for HealthEventResponse schema."""

    def test_health_event_response_required_fields(self):
        """Response should require all non-nullable fields."""
        event = HealthEventResponse(
            id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        assert event.id is not None
        assert event.category_id is not None
        assert event.occurred_at is not None
        assert event.created_at is not None
        assert event.notes is None  # Optional
        assert event.photos == []  # Defaults to empty list

    def test_health_event_response_with_notes(self):
        """Response should include notes when provided."""
        event = HealthEventResponse(
            id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            notes="Test notes",
            created_at=datetime.now(UTC),
        )

        assert event.notes == "Test notes"

    def test_health_event_response_with_photos(self):
        """Response should include nested photos."""
        photos = [
            HealthEventPhotoResponse(
                id=uuid4(),
                photo_url="https://example.com/1.jpg",
                sort_order=0,
                created_at=datetime.now(UTC),
            ),
            HealthEventPhotoResponse(
                id=uuid4(),
                photo_url="https://example.com/2.jpg",
                sort_order=1,
                created_at=datetime.now(UTC),
            ),
        ]

        event = HealthEventResponse(
            id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            photos=photos,
        )

        assert len(event.photos) == 2
        assert event.photos[0].sort_order == 0
        assert event.photos[1].sort_order == 1

    def test_health_event_response_empty_photos_list(self):
        """Response should handle empty photos list."""
        event = HealthEventResponse(
            id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            photos=[],
        )

        assert event.photos == []
        assert isinstance(event.photos, list)

    def test_health_event_response_from_attributes(self):
        """Response should support from_attributes for ORM models."""
        assert HealthEventResponse.model_config["from_attributes"] is True


class TestHealthEventNested:
    """Tests for HealthEventNested schema (for nested responses)."""

    def test_health_event_nested_required_fields(self):
        """Nested event should include pet_id and created_by."""
        event = HealthEventNested(
            id=uuid4(),
            pet_id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        assert event.id is not None
        assert event.pet_id is not None
        assert event.category_id is not None
        assert event.occurred_at is not None
        assert event.created_at is not None
        assert event.created_by is None  # Optional
        assert event.notes is None
        assert event.photos == []

    def test_health_event_nested_with_created_by(self):
        """Nested event should include created_by user ID."""
        user_id = uuid4()
        event = HealthEventNested(
            id=uuid4(),
            pet_id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            created_by=user_id,
        )

        assert event.created_by == user_id

    def test_health_event_nested_with_all_fields(self):
        """Nested event should support all optional fields."""
        user_id = uuid4()
        photos = [
            HealthEventPhotoResponse(
                id=uuid4(),
                photo_url="https://example.com/photo.jpg",
                sort_order=0,
                created_at=datetime.now(UTC),
            ),
        ]

        event = HealthEventNested(
            id=uuid4(),
            pet_id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            notes="Detailed notes",
            photos=photos,
            created_at=datetime.now(UTC),
            created_by=user_id,
        )

        assert event.notes == "Detailed notes"
        assert len(event.photos) == 1
        assert event.created_by == user_id

    def test_health_event_nested_from_attributes(self):
        """Nested response should support from_attributes for ORM models."""
        assert HealthEventNested.model_config["from_attributes"] is True


class TestHealthEventWithCategory:
    """Tests for HealthEventWithCategory schema (iOS-optimized nested structure)."""

    def test_health_event_with_category_structure(self):
        """Should nest event and category for iOS consumption."""
        event = HealthEventNested(
            id=uuid4(),
            pet_id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        category = HealthCategoryResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Vaccination",
            name_normalized="vaccination",
            created_at=datetime.now(UTC),
        )

        combined = HealthEventWithCategory(
            event=event,
            category=category,
        )

        assert combined.event.id == event.id
        assert combined.category.name == "Vaccination"

    def test_health_event_with_category_full_data(self):
        """Should include complete event and category details."""
        photos = [
            HealthEventPhotoResponse(
                id=uuid4(),
                photo_url="https://example.com/vax.jpg",
                sort_order=0,
                created_at=datetime.now(UTC),
            ),
        ]

        event = HealthEventNested(
            id=uuid4(),
            pet_id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            notes="Annual vaccination complete",
            photos=photos,
            created_at=datetime.now(UTC),
            created_by=uuid4(),
        )

        category = HealthCategoryResponse(
            id=event.category_id,
            family_id=uuid4(),
            name="Vaccination",
            name_normalized="vaccination",
            created_at=datetime.now(UTC),
            created_by=event.created_by,
        )

        combined = HealthEventWithCategory(
            event=event,
            category=category,
        )

        assert combined.event.notes == "Annual vaccination complete"
        assert len(combined.event.photos) == 1
        assert combined.category.name == "Vaccination"
        assert combined.event.category_id == combined.category.id


class TestHealthEventListResponse:
    """Tests for HealthEventListResponse wrapper schema."""

    def test_health_event_list_response_empty(self):
        """Should handle empty events list."""
        response = HealthEventListResponse(events=[])

        assert response.events == []
        assert isinstance(response.events, list)

    def test_health_event_list_response_single_event(self):
        """Should handle single event with category."""
        event = HealthEventNested(
            id=uuid4(),
            pet_id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        category = HealthCategoryResponse(
            id=event.category_id,
            family_id=uuid4(),
            name="Weight Check",
            name_normalized="weight check",
            created_at=datetime.now(UTC),
        )

        response = HealthEventListResponse(
            events=[
                HealthEventWithCategory(event=event, category=category),
            ]
        )

        assert len(response.events) == 1
        assert response.events[0].category.name == "Weight Check"

    def test_health_event_list_response_multiple_events(self):
        """Should handle multiple events with different categories."""
        events_data = [
            ("Vaccination", "vaccination"),
            ("Weight Check", "weight check"),
            ("Dental Cleaning", "dental cleaning"),
        ]

        events = []
        for name, normalized in events_data:
            event = HealthEventNested(
                id=uuid4(),
                pet_id=uuid4(),
                category_id=uuid4(),
                occurred_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )

            category = HealthCategoryResponse(
                id=event.category_id,
                family_id=uuid4(),
                name=name,
                name_normalized=normalized,
                created_at=datetime.now(UTC),
            )

            events.append(HealthEventWithCategory(event=event, category=category))

        response = HealthEventListResponse(events=events)

        assert len(response.events) == 3
        assert response.events[0].category.name == "Vaccination"
        assert response.events[1].category.name == "Weight Check"
        assert response.events[2].category.name == "Dental Cleaning"

    def test_health_event_list_response_preserves_photos(self):
        """Should preserve photos in nested events."""
        photos = [
            HealthEventPhotoResponse(
                id=uuid4(),
                photo_url="https://example.com/1.jpg",
                sort_order=0,
                created_at=datetime.now(UTC),
            ),
            HealthEventPhotoResponse(
                id=uuid4(),
                photo_url="https://example.com/2.jpg",
                sort_order=1,
                created_at=datetime.now(UTC),
            ),
        ]

        event = HealthEventNested(
            id=uuid4(),
            pet_id=uuid4(),
            category_id=uuid4(),
            occurred_at=datetime.now(UTC),
            photos=photos,
            created_at=datetime.now(UTC),
        )

        category = HealthCategoryResponse(
            id=event.category_id,
            family_id=uuid4(),
            name="Surgery",
            name_normalized="surgery",
            created_at=datetime.now(UTC),
        )

        response = HealthEventListResponse(
            events=[HealthEventWithCategory(event=event, category=category)]
        )

        assert len(response.events[0].event.photos) == 2


class TestHealthCategoryListResponse:
    """Tests for HealthCategoryListResponse wrapper schema."""

    def test_health_category_list_response_empty(self):
        """Should handle empty categories list."""
        response = HealthCategoryListResponse(categories=[])

        assert response.categories == []
        assert isinstance(response.categories, list)

    def test_health_category_list_response_single_category(self):
        """Should handle single category."""
        category = HealthCategoryResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Vaccination",
            name_normalized="vaccination",
            created_at=datetime.now(UTC),
        )

        response = HealthCategoryListResponse(categories=[category])

        assert len(response.categories) == 1
        assert response.categories[0].name == "Vaccination"

    def test_health_category_list_response_multiple_categories(self):
        """Should handle multiple categories."""
        categories = [
            HealthCategoryResponse(
                id=uuid4(),
                family_id=uuid4(),
                name=name,
                name_normalized=name.lower(),
                created_at=datetime.now(UTC),
            )
            for name in ["Vaccination", "Weight Check", "Dental", "Surgery", "Lab Work"]
        ]

        response = HealthCategoryListResponse(categories=categories)

        assert len(response.categories) == 5
        category_names = [cat.name for cat in response.categories]
        assert "Vaccination" in category_names
        assert "Weight Check" in category_names
        assert "Surgery" in category_names

    def test_health_category_list_response_preserves_metadata(self):
        """Should preserve all category metadata."""
        user_id = uuid4()
        family_id = uuid4()
        created_time = datetime.now(UTC)

        category = HealthCategoryResponse(
            id=uuid4(),
            family_id=family_id,
            name="Custom Category",
            name_normalized="custom category",
            created_at=created_time,
            created_by=user_id,
        )

        response = HealthCategoryListResponse(categories=[category])

        assert response.categories[0].family_id == family_id
        assert response.categories[0].created_by == user_id
        assert response.categories[0].created_at == created_time


class TestSchemaValidation:
    """Tests for schema validation and edge cases."""

    def test_health_event_create_missing_required_field(self):
        """Should raise validation error when required field is missing."""
        with pytest.raises(ValidationError) as exc_info:
            HealthEventCreate()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("category_name",) for error in errors)

    def test_health_category_create_missing_required_field(self):
        """Should raise validation error when required field is missing."""
        with pytest.raises(ValidationError) as exc_info:
            HealthCategoryCreate()

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("name",) for error in errors)

    def test_health_event_response_missing_required_field(self):
        """Should raise validation error when required field is missing."""
        with pytest.raises(ValidationError) as exc_info:
            HealthEventResponse(
                id=uuid4(),
                # Missing category_id, occurred_at, created_at
            )

        errors = exc_info.value.errors()
        assert len(errors) >= 1  # At least one required field missing

    def test_invalid_uuid_format(self):
        """Should raise validation error for invalid UUID."""
        with pytest.raises(ValidationError):
            HealthEventResponse(
                id="not-a-uuid",  # Invalid UUID format
                category_id=uuid4(),
                occurred_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )

    def test_invalid_datetime_format(self):
        """Should raise validation error for invalid datetime."""
        with pytest.raises(ValidationError):
            HealthEventCreate(
                category_name="Test",
                occurred_at="not-a-datetime",  # Invalid datetime
            )

    def test_none_values_for_optional_fields(self):
        """Should accept None for all optional fields."""
        event = HealthEventCreate(
            category_name="Test",
            occurred_at=None,
            notes=None,
            notify_family=False,
        )

        assert event.occurred_at is None
        assert event.notes is None

    def test_boolean_field_accepts_bool_only(self):
        """Notify family should accept boolean values."""
        event_true = HealthEventCreate(
            category_name="Test",
            notify_family=True,
        )

        event_false = HealthEventCreate(
            category_name="Test",
            notify_family=False,
        )

        assert event_true.notify_family is True
        assert event_false.notify_family is False
