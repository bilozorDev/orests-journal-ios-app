"""
Tests for Feeding Pydantic schemas.

Validates feeding schema behavior to prevent breaking changes to iOS app.
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.food import (
    FeedingCreate,
    FeedingUpdate,
    FeedingResponse,
    FeedingListResponse,
)
from app.models.food import ContainerUnit


class TestFeedingCreate:
    """Tests for FeedingCreate schema."""

    def test_feeding_create_required_fields_only(self):
        """Should create feeding with only required fields."""
        feeding = FeedingCreate(
            pet_id=uuid4(),
            food_id=uuid4(),
            amount=150.0,
            calories=175.0,
        )

        assert feeding.pet_id is not None
        assert feeding.food_id is not None
        assert feeding.amount == 150.0
        assert feeding.calories == 175.0
        assert feeding.amount_unit == ContainerUnit.GRAMS  # Default
        assert feeding.notes is None
        assert feeding.fed_at is None  # Defaults to None (will be set to now in endpoint)

    def test_feeding_create_with_all_fields(self):
        """Should create feeding with all optional fields."""
        fed_time = datetime.now(UTC) - timedelta(hours=2)

        feeding = FeedingCreate(
            pet_id=uuid4(),
            food_id=uuid4(),
            amount=150.0,
            amount_unit=ContainerUnit.OUNCES,
            calories=175.0,
            notes="Fed with medication",
            fed_at=fed_time,
        )

        assert feeding.amount == 150.0
        assert feeding.amount_unit == ContainerUnit.OUNCES
        assert feeding.calories == 175.0
        assert feeding.notes == "Fed with medication"
        assert feeding.fed_at == fed_time

    def test_feeding_create_amount_unit_defaults_to_grams(self):
        """Amount unit should default to grams."""
        feeding = FeedingCreate(
            pet_id=uuid4(),
            food_id=uuid4(),
            amount=150.0,
            calories=175.0,
        )

        assert feeding.amount_unit == ContainerUnit.GRAMS

    def test_feeding_create_fed_at_defaults_to_none(self):
        """fed_at should default to None (will be set to now in endpoint)."""
        feeding = FeedingCreate(
            pet_id=uuid4(),
            food_id=uuid4(),
            amount=150.0,
            calories=175.0,
        )

        assert feeding.fed_at is None

    def test_feeding_create_with_custom_timestamp(self):
        """Should accept custom fed_at timestamp."""
        past_time = datetime.now(UTC) - timedelta(hours=5)

        feeding = FeedingCreate(
            pet_id=uuid4(),
            food_id=uuid4(),
            amount=150.0,
            calories=175.0,
            fed_at=past_time,
        )

        assert feeding.fed_at == past_time

    def test_feeding_create_missing_required_field_raises_error(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FeedingCreate(
                pet_id=uuid4(),
                food_id=uuid4(),
                amount=150.0,
                # Missing calories
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("calories",) for e in errors)

    def test_feeding_create_amount_must_be_numeric(self):
        """Amount must be a number."""
        with pytest.raises(ValidationError):
            FeedingCreate(
                pet_id=uuid4(),
                food_id=uuid4(),
                amount="not a number",  # type: ignore
                calories=175.0,
            )

    def test_feeding_create_calories_must_be_numeric(self):
        """Calories must be a number."""
        with pytest.raises(ValidationError):
            FeedingCreate(
                pet_id=uuid4(),
                food_id=uuid4(),
                amount=150.0,
                calories="not a number",  # type: ignore
            )

    def test_feeding_create_various_container_units(self):
        """Should accept all valid container units."""
        for unit in [ContainerUnit.GRAMS, ContainerUnit.OUNCES, ContainerUnit.KILOGRAMS, ContainerUnit.POUNDS]:
            feeding = FeedingCreate(
                pet_id=uuid4(),
                food_id=uuid4(),
                amount=150.0,
                amount_unit=unit,
                calories=175.0,
            )
            assert feeding.amount_unit == unit

    def test_feeding_create_with_notes(self):
        """Should accept notes field."""
        feeding = FeedingCreate(
            pet_id=uuid4(),
            food_id=uuid4(),
            amount=150.0,
            calories=175.0,
            notes="Ate slowly, seemed less hungry",
        )

        assert feeding.notes == "Ate slowly, seemed less hungry"

    def test_feeding_create_various_amounts(self):
        """Should accept various amounts and calorie values."""
        test_cases = [
            (50.0, 58.0),
            (100.5, 117.5),
            (200.0, 233.0),
        ]

        for amount, calories in test_cases:
            feeding = FeedingCreate(
                pet_id=uuid4(),
                food_id=uuid4(),
                amount=amount,
                calories=calories,
            )
            assert feeding.amount == amount
            assert feeding.calories == calories


class TestFeedingUpdate:
    """Tests for FeedingUpdate schema."""

    def test_feeding_update_all_fields_optional(self):
        """All fields in update schema should be optional."""
        update = FeedingUpdate()

        assert update.amount is None
        assert update.amount_unit is None
        assert update.calories is None
        assert update.notes is None
        assert update.fed_at is None
        assert update.fed_by is None

    def test_feeding_update_single_field(self):
        """Should allow updating a single field."""
        update = FeedingUpdate(amount=200.0)

        assert update.amount == 200.0
        assert update.calories is None  # Other fields remain None

    def test_feeding_update_multiple_fields(self):
        """Should allow updating multiple fields."""
        update = FeedingUpdate(
            amount=200.0,
            calories=233.0,
            notes="Updated feeding notes",
        )

        assert update.amount == 200.0
        assert update.calories == 233.0
        assert update.notes == "Updated feeding notes"

    def test_feeding_update_amount_unit(self):
        """Should allow updating amount unit."""
        update = FeedingUpdate(amount_unit=ContainerUnit.POUNDS)

        assert update.amount_unit == ContainerUnit.POUNDS

    def test_feeding_update_fed_at(self):
        """Should allow updating fed_at timestamp."""
        new_time = datetime.now(UTC) - timedelta(hours=1)

        update = FeedingUpdate(fed_at=new_time)

        assert update.fed_at == new_time

    def test_feeding_update_fed_by(self):
        """Should allow updating fed_by user."""
        user_id = uuid4()

        update = FeedingUpdate(fed_by=user_id)

        assert update.fed_by == user_id

    def test_feeding_update_notes(self):
        """Should allow updating notes."""
        update = FeedingUpdate(notes="Pet was very hungry")

        assert update.notes == "Pet was very hungry"

    def test_feeding_update_remove_notes(self):
        """Should allow explicitly setting notes to None."""
        update = FeedingUpdate(notes=None)

        assert update.notes is None


class TestFeedingResponse:
    """Tests for FeedingResponse schema."""

    def test_feeding_response_required_fields(self):
        """Response should require all non-nullable fields."""
        response = FeedingResponse(
            id=uuid4(),
            pet_id=uuid4(),
            food_id=uuid4(),
            fed_by=uuid4(),
            fed_at=datetime.now(UTC),
            amount=150.0,
            amount_unit=ContainerUnit.GRAMS,
            calories=175.0,
            created_at=datetime.now(UTC),
        )

        assert response.id is not None
        assert response.pet_id is not None
        assert response.food_id is not None
        assert response.fed_by is not None
        assert response.fed_at is not None
        assert response.amount == 150.0
        assert response.amount_unit == ContainerUnit.GRAMS
        assert response.calories == 175.0
        assert response.created_at is not None

    def test_feeding_response_defaults(self):
        """Response should include default values for optional fields."""
        response = FeedingResponse(
            id=uuid4(),
            pet_id=uuid4(),
            food_id=uuid4(),
            fed_by=uuid4(),
            fed_at=datetime.now(UTC),
            amount=150.0,
            amount_unit=ContainerUnit.GRAMS,
            calories=175.0,
            created_at=datetime.now(UTC),
        )

        assert response.notes is None

    def test_feeding_response_with_notes(self):
        """Response should include notes when provided."""
        response = FeedingResponse(
            id=uuid4(),
            pet_id=uuid4(),
            food_id=uuid4(),
            fed_by=uuid4(),
            fed_at=datetime.now(UTC),
            amount=150.0,
            amount_unit=ContainerUnit.GRAMS,
            calories=175.0,
            notes="Fed in the morning",
            created_at=datetime.now(UTC),
        )

        assert response.notes == "Fed in the morning"

    def test_feeding_response_various_units(self):
        """Response should handle all container units."""
        for unit in [ContainerUnit.GRAMS, ContainerUnit.OUNCES, ContainerUnit.KILOGRAMS, ContainerUnit.POUNDS]:
            response = FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=150.0,
                amount_unit=unit,
                calories=175.0,
                created_at=datetime.now(UTC),
            )
            assert response.amount_unit == unit

    def test_feeding_response_various_amounts_and_calories(self):
        """Response should handle various amounts and calories."""
        test_cases = [
            (50.0, 58.0),
            (100.5, 117.5),
            (200.0, 233.0),
        ]

        for amount, calories in test_cases:
            response = FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=amount,
                amount_unit=ContainerUnit.GRAMS,
                calories=calories,
                created_at=datetime.now(UTC),
            )
            assert response.amount == amount
            assert response.calories == calories

    def test_feeding_response_fed_at_timestamp(self):
        """Response should preserve fed_at timestamp."""
        fed_time = datetime.now(UTC) - timedelta(hours=3)

        response = FeedingResponse(
            id=uuid4(),
            pet_id=uuid4(),
            food_id=uuid4(),
            fed_by=uuid4(),
            fed_at=fed_time,
            amount=150.0,
            amount_unit=ContainerUnit.GRAMS,
            calories=175.0,
            created_at=datetime.now(UTC),
        )

        assert response.fed_at == fed_time


class TestFeedingListResponse:
    """Tests for FeedingListResponse schema."""

    def test_feeding_list_response_empty_list(self):
        """Should handle empty feeding list."""
        response = FeedingListResponse(feedings=[])

        assert response.feedings == []
        assert response.total_calories == 0
        assert response.total == 0
        assert len(response.feedings) == 0

    def test_feeding_list_response_defaults(self):
        """Should have default values for totals."""
        response = FeedingListResponse(feedings=[])

        assert response.total_calories == 0
        assert response.total == 0

    def test_feeding_list_response_with_feedings(self):
        """Should contain list of feedings with totals."""
        feedings = [
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=150.0,
                amount_unit=ContainerUnit.GRAMS,
                calories=175.0,
                created_at=datetime.now(UTC),
            ),
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=100.0,
                amount_unit=ContainerUnit.GRAMS,
                calories=116.5,
                created_at=datetime.now(UTC),
            ),
        ]

        response = FeedingListResponse(
            feedings=feedings,
            total_calories=291.5,
            total=2,
        )

        assert len(response.feedings) == 2
        assert response.total_calories == 291.5
        assert response.total == 2

    def test_feeding_list_response_total_calories_calculation(self):
        """Should include correct total_calories sum."""
        feedings = [
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=150.0,
                amount_unit=ContainerUnit.GRAMS,
                calories=175.0,
                created_at=datetime.now(UTC),
            ),
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=100.0,
                amount_unit=ContainerUnit.GRAMS,
                calories=116.5,
                created_at=datetime.now(UTC),
            ),
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=75.0,
                amount_unit=ContainerUnit.GRAMS,
                calories=87.5,
                created_at=datetime.now(UTC),
            ),
        ]

        # Total: 175 + 116.5 + 87.5 = 379
        response = FeedingListResponse(
            feedings=feedings,
            total_calories=379.0,
            total=3,
        )

        assert response.total_calories == 379.0
        assert response.total == 3
        assert len(response.feedings) == 3

    def test_feeding_list_response_pagination_count(self):
        """Should track total count for pagination separately from list length."""
        # Simulate pagination: page 1 of 2 (showing 2 items, total 5)
        feedings = [
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=150.0,
                amount_unit=ContainerUnit.GRAMS,
                calories=175.0,
                created_at=datetime.now(UTC),
            ),
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=100.0,
                amount_unit=ContainerUnit.GRAMS,
                calories=116.5,
                created_at=datetime.now(UTC),
            ),
        ]

        response = FeedingListResponse(
            feedings=feedings,
            total_calories=291.5,
            total=5,  # Total count across all pages
        )

        assert len(response.feedings) == 2  # Current page
        assert response.total == 5  # Total across all pages
        assert response.total_calories == 291.5  # Sum for current page

    def test_feeding_list_response_zero_calories(self):
        """Should handle zero calories correctly."""
        response = FeedingListResponse(
            feedings=[],
            total_calories=0.0,
            total=0,
        )

        assert response.total_calories == 0.0

    def test_feeding_list_response_mixed_units(self):
        """Should handle feedings with different units."""
        feedings = [
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=150.0,
                amount_unit=ContainerUnit.GRAMS,
                calories=175.0,
                created_at=datetime.now(UTC),
            ),
            FeedingResponse(
                id=uuid4(),
                pet_id=uuid4(),
                food_id=uuid4(),
                fed_by=uuid4(),
                fed_at=datetime.now(UTC),
                amount=3.5,
                amount_unit=ContainerUnit.OUNCES,
                calories=116.5,
                created_at=datetime.now(UTC),
            ),
        ]

        response = FeedingListResponse(
            feedings=feedings,
            total_calories=291.5,
            total=2,
        )

        assert len(response.feedings) == 2
        assert response.feedings[0].amount_unit == ContainerUnit.GRAMS
        assert response.feedings[1].amount_unit == ContainerUnit.OUNCES
