"""
Tests for Food Pydantic schemas.

Validates food schema behavior to prevent breaking changes to iOS app.
"""
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.food import (
    FoodCreate,
    FoodUpdate,
    FoodResponse,
    FoodListResponse,
    FoodDeleteResponse,
    CalorieGoalCreate,
    CalorieGoalResponse,
)
from app.models.food import FoodCategory, ContainerUnit


class TestFoodCategory:
    """Tests for FoodCategory enum."""

    def test_food_category_all_values_valid(self):
        """All 3 food categories should be valid."""
        valid_categories = ["dry", "wet", "snack"]

        for category in valid_categories:
            # Should not raise
            result = FoodCategory(category)
            assert result.value == category

    def test_food_category_invalid_value_raises_error(self):
        """Invalid food category should raise ValueError."""
        with pytest.raises(ValueError):
            FoodCategory("raw")

    def test_food_category_case_sensitive(self):
        """Food categories are case-sensitive."""
        with pytest.raises(ValueError):
            FoodCategory("DRY")  # Must be lowercase

    def test_food_category_enum_count(self):
        """Should have exactly 3 food categories."""
        assert len(FoodCategory) == 3


class TestContainerUnit:
    """Tests for ContainerUnit enum."""

    def test_container_unit_all_values_valid(self):
        """All 4 container units should be valid."""
        valid_units = ["g", "oz", "kg", "lb"]

        for unit in valid_units:
            # Should not raise
            result = ContainerUnit(unit)
            assert result.value == unit

    def test_container_unit_invalid_value_raises_error(self):
        """Invalid container unit should raise ValueError."""
        with pytest.raises(ValueError):
            ContainerUnit("ml")

    def test_container_unit_case_sensitive(self):
        """Container units are case-sensitive."""
        with pytest.raises(ValueError):
            ContainerUnit("G")  # Must be lowercase

    def test_container_unit_enum_count(self):
        """Should have exactly 4 container units."""
        assert len(ContainerUnit) == 4


class TestFoodCreate:
    """Tests for FoodCreate schema."""

    def test_food_create_required_fields_only(self):
        """Should create food with only required fields."""
        food = FoodCreate(
            name="Blue Buffalo Adult",
            category=FoodCategory.DRY,
            calories_per_kg=3500.0,
            container_size=15.0,
        )

        assert food.name == "Blue Buffalo Adult"
        assert food.category == FoodCategory.DRY
        assert food.calories_per_kg == 3500.0
        assert food.container_size == 15.0
        assert food.container_size_unit == ContainerUnit.GRAMS  # Default
        assert food.image_url is None

    def test_food_create_with_all_fields(self):
        """Should create food with all optional fields."""
        food = FoodCreate(
            name="Fancy Feast Pate",
            category=FoodCategory.WET,
            calories_per_kg=850.0,
            container_size=3.0,
            container_size_unit=ContainerUnit.OUNCES,
            image_url="https://example.com/food.jpg",
        )

        assert food.name == "Fancy Feast Pate"
        assert food.category == FoodCategory.WET
        assert food.calories_per_kg == 850.0
        assert food.container_size == 3.0
        assert food.container_size_unit == ContainerUnit.OUNCES
        assert food.image_url == "https://example.com/food.jpg"

    def test_food_create_container_size_unit_defaults_to_grams(self):
        """Container size unit should default to grams."""
        food = FoodCreate(
            name="Test Food",
            category=FoodCategory.SNACK,
            calories_per_kg=3000.0,
            container_size=500.0,
        )

        assert food.container_size_unit == ContainerUnit.GRAMS

    def test_food_create_missing_required_field_raises_error(self):
        """Missing required fields should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            FoodCreate(
                name="Test Food",
                category=FoodCategory.DRY,
                calories_per_kg=3500.0,
                # Missing container_size
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("container_size",) for e in errors)

    def test_food_create_calories_must_be_numeric(self):
        """Calories per kg must be a number."""
        with pytest.raises(ValidationError):
            FoodCreate(
                name="Test Food",
                category=FoodCategory.DRY,
                calories_per_kg="not a number",  # type: ignore
                container_size=15.0,
            )

    def test_food_create_container_size_must_be_numeric(self):
        """Container size must be a number."""
        with pytest.raises(ValidationError):
            FoodCreate(
                name="Test Food",
                category=FoodCategory.DRY,
                calories_per_kg=3500.0,
                container_size="not a number",  # type: ignore
            )

    def test_food_create_various_container_units(self):
        """Should accept all valid container units."""
        for unit in [ContainerUnit.GRAMS, ContainerUnit.OUNCES, ContainerUnit.KILOGRAMS, ContainerUnit.POUNDS]:
            food = FoodCreate(
                name="Test Food",
                category=FoodCategory.DRY,
                calories_per_kg=3500.0,
                container_size=10.0,
                container_size_unit=unit,
            )
            assert food.container_size_unit == unit

    def test_food_create_various_categories(self):
        """Should accept all valid food categories."""
        for category in [FoodCategory.DRY, FoodCategory.WET, FoodCategory.SNACK]:
            food = FoodCreate(
                name="Test Food",
                category=category,
                calories_per_kg=3500.0,
                container_size=10.0,
            )
            assert food.category == category


class TestFoodUpdate:
    """Tests for FoodUpdate schema."""

    def test_food_update_all_fields_optional(self):
        """All fields in update schema should be optional."""
        update = FoodUpdate()

        assert update.name is None
        assert update.category is None
        assert update.calories_per_kg is None
        assert update.container_size is None
        assert update.container_size_unit is None
        assert update.image_url is None

    def test_food_update_single_field(self):
        """Should allow updating a single field."""
        update = FoodUpdate(name="Updated Food Name")

        assert update.name == "Updated Food Name"
        assert update.category is None  # Other fields remain None

    def test_food_update_multiple_fields(self):
        """Should allow updating multiple fields."""
        update = FoodUpdate(
            name="Updated Food",
            calories_per_kg=4000.0,
            container_size=20.0,
        )

        assert update.name == "Updated Food"
        assert update.calories_per_kg == 4000.0
        assert update.container_size == 20.0

    def test_food_update_category_change(self):
        """Should allow changing food category."""
        update = FoodUpdate(category=FoodCategory.WET)

        assert update.category == FoodCategory.WET

    def test_food_update_container_unit_change(self):
        """Should allow changing container unit."""
        update = FoodUpdate(container_size_unit=ContainerUnit.POUNDS)

        assert update.container_size_unit == ContainerUnit.POUNDS

    def test_food_update_image_url(self):
        """Should allow updating image URL."""
        update = FoodUpdate(image_url="https://example.com/new-image.jpg")

        assert update.image_url == "https://example.com/new-image.jpg"

    def test_food_update_remove_image_url(self):
        """Should allow explicitly setting image_url to None."""
        update = FoodUpdate(image_url=None)

        assert update.image_url is None


class TestFoodResponse:
    """Tests for FoodResponse schema."""

    def test_food_response_required_fields(self):
        """Response should require all non-nullable fields."""
        response = FoodResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Test Food",
            category=FoodCategory.DRY,
            calories_per_kg=3500.0,
            container_size=15.0,
            container_size_unit=ContainerUnit.GRAMS,
            created_at=datetime.now(UTC),
        )

        assert response.id is not None
        assert response.family_id is not None
        assert response.name == "Test Food"
        assert response.category == FoodCategory.DRY
        assert response.calories_per_kg == 3500.0
        assert response.container_size == 15.0
        assert response.container_size_unit == ContainerUnit.GRAMS
        assert response.created_at is not None

    def test_food_response_defaults(self):
        """Response should include default values."""
        response = FoodResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Test Food",
            category=FoodCategory.DRY,
            calories_per_kg=3500.0,
            container_size=15.0,
            container_size_unit=ContainerUnit.GRAMS,
            created_at=datetime.now(UTC),
        )

        assert response.is_archived is False
        assert response.image_url is None

    def test_food_response_with_image_url(self):
        """Response should include image URL when provided."""
        response = FoodResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Test Food",
            category=FoodCategory.DRY,
            calories_per_kg=3500.0,
            container_size=15.0,
            container_size_unit=ContainerUnit.GRAMS,
            image_url="https://example.com/food.jpg",
            created_at=datetime.now(UTC),
        )

        assert response.image_url == "https://example.com/food.jpg"

    def test_food_response_archived_food(self):
        """Response should handle archived foods."""
        response = FoodResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Archived Food",
            category=FoodCategory.DRY,
            calories_per_kg=3500.0,
            container_size=15.0,
            container_size_unit=ContainerUnit.GRAMS,
            is_archived=True,
            created_at=datetime.now(UTC),
        )

        assert response.is_archived is True

    def test_food_response_various_units_and_categories(self):
        """Response should handle all unit and category combinations."""
        response = FoodResponse(
            id=uuid4(),
            family_id=uuid4(),
            name="Test Food",
            category=FoodCategory.WET,
            calories_per_kg=850.0,
            container_size=3.0,
            container_size_unit=ContainerUnit.OUNCES,
            created_at=datetime.now(UTC),
        )

        assert response.category == FoodCategory.WET
        assert response.container_size_unit == ContainerUnit.OUNCES


class TestFoodListResponse:
    """Tests for FoodListResponse schema."""

    def test_food_list_response_empty_list(self):
        """Should handle empty food list."""
        response = FoodListResponse(foods=[])

        assert response.foods == []
        assert len(response.foods) == 0

    def test_food_list_response_with_foods(self):
        """Should contain list of foods."""
        foods = [
            FoodResponse(
                id=uuid4(),
                family_id=uuid4(),
                name="Food 1",
                category=FoodCategory.DRY,
                calories_per_kg=3500.0,
                container_size=15.0,
                container_size_unit=ContainerUnit.GRAMS,
                created_at=datetime.now(UTC),
            ),
            FoodResponse(
                id=uuid4(),
                family_id=uuid4(),
                name="Food 2",
                category=FoodCategory.WET,
                calories_per_kg=850.0,
                container_size=3.0,
                container_size_unit=ContainerUnit.OUNCES,
                created_at=datetime.now(UTC),
            ),
        ]

        response = FoodListResponse(foods=foods)

        assert len(response.foods) == 2
        assert response.foods[0].name == "Food 1"
        assert response.foods[1].name == "Food 2"


class TestFoodDeleteResponse:
    """Tests for FoodDeleteResponse schema."""

    def test_food_delete_response_hard_delete(self):
        """Should handle hard delete (no feedings)."""
        response = FoodDeleteResponse(
            deleted=True,
            archived=False,
            message="Food deleted successfully",
        )

        assert response.deleted is True
        assert response.archived is False
        assert response.message == "Food deleted successfully"

    def test_food_delete_response_soft_delete(self):
        """Should handle soft delete (archived due to feedings)."""
        response = FoodDeleteResponse(
            deleted=False,
            archived=True,
            message="Food archived successfully",
        )

        assert response.deleted is False
        assert response.archived is True
        assert response.message == "Food archived successfully"

    def test_food_delete_response_all_fields_required(self):
        """All fields should be required."""
        with pytest.raises(ValidationError):
            FoodDeleteResponse(
                deleted=True,
                archived=False,
                # Missing message
            )


class TestCalorieGoalCreate:
    """Tests for CalorieGoalCreate schema."""

    def test_calorie_goal_create_required_field_only(self):
        """Should create calorie goal with only required field."""
        goal = CalorieGoalCreate(daily_calories=450.0)

        assert goal.daily_calories == 450.0
        assert goal.notes is None

    def test_calorie_goal_create_with_notes(self):
        """Should create calorie goal with notes."""
        goal = CalorieGoalCreate(
            daily_calories=450.0,
            notes="Adjusted for weight loss",
        )

        assert goal.daily_calories == 450.0
        assert goal.notes == "Adjusted for weight loss"

    def test_calorie_goal_create_missing_daily_calories_raises_error(self):
        """Missing daily_calories should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            CalorieGoalCreate(notes="Test notes")  # type: ignore

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("daily_calories",) for e in errors)

    def test_calorie_goal_create_daily_calories_must_be_numeric(self):
        """Daily calories must be a number."""
        with pytest.raises(ValidationError):
            CalorieGoalCreate(daily_calories="not a number")  # type: ignore

    def test_calorie_goal_create_various_calorie_amounts(self):
        """Should accept various calorie amounts."""
        for calories in [100.0, 250.5, 500.0, 1000.0]:
            goal = CalorieGoalCreate(daily_calories=calories)
            assert goal.daily_calories == calories


class TestCalorieGoalResponse:
    """Tests for CalorieGoalResponse schema."""

    def test_calorie_goal_response_required_fields(self):
        """Response should require all non-nullable fields."""
        response = CalorieGoalResponse(
            id=uuid4(),
            pet_id=uuid4(),
            daily_calories=450.0,
            effective_from=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        assert response.id is not None
        assert response.pet_id is not None
        assert response.daily_calories == 450.0
        assert response.effective_from is not None
        assert response.created_at is not None

    def test_calorie_goal_response_defaults(self):
        """Response should include default values for optional fields."""
        response = CalorieGoalResponse(
            id=uuid4(),
            pet_id=uuid4(),
            daily_calories=450.0,
            effective_from=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )

        assert response.effective_until is None
        assert response.notes is None

    def test_calorie_goal_response_with_effective_until(self):
        """Response should handle effective_until date."""
        effective_from = datetime.now(UTC)
        effective_until = datetime.now(UTC)

        response = CalorieGoalResponse(
            id=uuid4(),
            pet_id=uuid4(),
            daily_calories=450.0,
            effective_from=effective_from,
            effective_until=effective_until,
            created_at=datetime.now(UTC),
        )

        assert response.effective_from == effective_from
        assert response.effective_until == effective_until

    def test_calorie_goal_response_with_notes(self):
        """Response should include notes when provided."""
        response = CalorieGoalResponse(
            id=uuid4(),
            pet_id=uuid4(),
            daily_calories=450.0,
            effective_from=datetime.now(UTC),
            notes="Weight loss plan",
            created_at=datetime.now(UTC),
        )

        assert response.notes == "Weight loss plan"

    def test_calorie_goal_response_various_calorie_amounts(self):
        """Response should handle various calorie amounts."""
        for calories in [100.0, 250.5, 500.0, 1000.0]:
            response = CalorieGoalResponse(
                id=uuid4(),
                pet_id=uuid4(),
                daily_calories=calories,
                effective_from=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
            assert response.daily_calories == calories
