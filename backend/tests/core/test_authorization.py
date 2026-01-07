"""Unit tests for authorization module.

Tests the authorization helper functions that verify family membership,
admin access, and resource access (pets, medications, doses, etc.).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi import HTTPException

from app.core.authorization import (
    verify_family_access,
    verify_admin_access,
    verify_pet_access,
    verify_medication_access,
    verify_dose_access,
    verify_feeding_access,
    verify_health_event_access,
    verify_food_access,
    verify_calorie_goal_access,
    verify_health_category_access,
)
from app.models.user import FamilyMember
from app.models.pet import Pet
from app.models.medication import PetMedication, PetMedicationDose
from app.models.food import PetFood, PetFeeding, PetCalorieGoal
from app.models.health import PetHealthEvent, PetHealthCategory


# Test data
TEST_USER_ID = str(uuid4())
TEST_FAMILY_ID = uuid4()
TEST_PET_ID = uuid4()
TEST_MEDICATION_ID = uuid4()
TEST_DOSE_ID = uuid4()
TEST_FEEDING_ID = uuid4()
TEST_EVENT_ID = uuid4()
TEST_FOOD_ID = uuid4()
TEST_CALORIE_GOAL_ID = uuid4()
TEST_HEALTH_CATEGORY_ID = uuid4()


def create_mock_membership(role: str = "member") -> FamilyMember:
    """Create a mock family membership."""
    mock = MagicMock(spec=FamilyMember)
    mock.user_id = UUID(TEST_USER_ID)
    mock.family_id = TEST_FAMILY_ID
    mock.role = role
    return mock


def create_mock_pet() -> Pet:
    """Create a mock pet."""
    mock = MagicMock(spec=Pet)
    mock.id = TEST_PET_ID
    mock.family_id = TEST_FAMILY_ID
    mock.name = "Orest"
    return mock


def create_mock_medication() -> PetMedication:
    """Create a mock medication."""
    mock = MagicMock(spec=PetMedication)
    mock.id = TEST_MEDICATION_ID
    mock.pet_id = TEST_PET_ID
    return mock


def create_mock_dose() -> PetMedicationDose:
    """Create a mock dose."""
    mock = MagicMock(spec=PetMedicationDose)
    mock.id = TEST_DOSE_ID
    mock.medication_id = TEST_MEDICATION_ID
    return mock


def create_mock_feeding() -> PetFeeding:
    """Create a mock feeding."""
    mock = MagicMock(spec=PetFeeding)
    mock.id = TEST_FEEDING_ID
    mock.pet_id = TEST_PET_ID
    return mock


def create_mock_event() -> PetHealthEvent:
    """Create a mock health event."""
    mock = MagicMock(spec=PetHealthEvent)
    mock.id = TEST_EVENT_ID
    mock.pet_id = TEST_PET_ID
    return mock


def create_mock_food() -> PetFood:
    """Create a mock food."""
    mock = MagicMock(spec=PetFood)
    mock.id = TEST_FOOD_ID
    mock.family_id = TEST_FAMILY_ID
    return mock


def create_mock_calorie_goal() -> PetCalorieGoal:
    """Create a mock calorie goal."""
    mock = MagicMock(spec=PetCalorieGoal)
    mock.id = TEST_CALORIE_GOAL_ID
    mock.pet_id = TEST_PET_ID
    return mock


def create_mock_health_category() -> PetHealthCategory:
    """Create a mock health category."""
    mock = MagicMock(spec=PetHealthCategory)
    mock.id = TEST_HEALTH_CATEGORY_ID
    mock.family_id = TEST_FAMILY_ID
    return mock


class TestVerifyFamilyAccess:
    """Tests for verify_family_access function."""

    @pytest.mark.asyncio
    async def test_verify_family_access_success(self):
        """Should return membership when user is a family member."""
        mock_db = AsyncMock()
        mock_membership = create_mock_membership()

        # Mock the database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_membership
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_family_access(
                mock_db, TEST_USER_ID, str(TEST_FAMILY_ID)
            )

        assert result == mock_membership
        mock_db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_verify_family_access_not_member(self):
        """Should raise 403 when user is not a family member."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_family_access(
                    mock_db, TEST_USER_ID, str(TEST_FAMILY_ID)
                )

        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_family_access_handles_uuid_string(self):
        """Should handle both UUID and string family_id."""
        mock_db = AsyncMock()
        mock_membership = create_mock_membership()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_membership
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            # Test with string
            result = await verify_family_access(
                mock_db, TEST_USER_ID, str(TEST_FAMILY_ID)
            )
            assert result == mock_membership


class TestVerifyAdminAccess:
    """Tests for verify_admin_access function."""

    @pytest.mark.asyncio
    async def test_verify_admin_access_success(self):
        """Should return membership when user is an admin."""
        mock_db = AsyncMock()
        mock_membership = create_mock_membership(role="admin")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_membership
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_admin_access(
                mock_db, TEST_USER_ID, str(TEST_FAMILY_ID)
            )

        assert result == mock_membership
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_verify_admin_access_member_denied(self):
        """Should raise 403 when user is member but not admin."""
        mock_db = AsyncMock()
        mock_membership = create_mock_membership(role="member")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_membership
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_admin_access(
                    mock_db, TEST_USER_ID, str(TEST_FAMILY_ID)
                )

        assert exc_info.value.status_code == 403
        assert "admin" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_verify_admin_access_not_member(self):
        """Should raise 403 when user is not a family member at all."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_admin_access(
                    mock_db, TEST_USER_ID, str(TEST_FAMILY_ID)
                )

        assert exc_info.value.status_code == 403


class TestVerifyPetAccess:
    """Tests for verify_pet_access function."""

    @pytest.mark.asyncio
    async def test_verify_pet_access_success(self):
        """Should return pet when user has access."""
        mock_db = AsyncMock()
        mock_pet = create_mock_pet()
        mock_membership = create_mock_membership()

        # First call returns pet, second returns membership
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_pet

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = mock_membership

        mock_db.execute.side_effect = [mock_result1, mock_result2]

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_pet_access(
                mock_db, TEST_USER_ID, TEST_PET_ID
            )

        assert result == mock_pet

    @pytest.mark.asyncio
    async def test_verify_pet_access_pet_not_found(self):
        """Should raise 404 when pet doesn't exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_pet_access(mock_db, TEST_USER_ID, TEST_PET_ID)

        assert exc_info.value.status_code == 404
        assert "Pet not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_pet_access_wrong_family(self):
        """Should raise 403 when user doesn't have access to pet's family."""
        mock_db = AsyncMock()
        mock_pet = create_mock_pet()

        # First call returns pet, second returns no membership
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = mock_pet

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None

        mock_db.execute.side_effect = [mock_result1, mock_result2]

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_pet_access(mock_db, TEST_USER_ID, TEST_PET_ID)

        assert exc_info.value.status_code == 403


class TestVerifyMedicationAccess:
    """Tests for verify_medication_access function."""

    @pytest.mark.asyncio
    async def test_verify_medication_access_success(self):
        """Should return medication when user has access."""
        mock_db = AsyncMock()
        mock_medication = create_mock_medication()
        mock_pet = create_mock_pet()
        mock_membership = create_mock_membership()

        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_medication)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_pet)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_membership)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_medication_access(
                mock_db, TEST_USER_ID, TEST_MEDICATION_ID
            )

        assert result == mock_medication

    @pytest.mark.asyncio
    async def test_verify_medication_access_not_found(self):
        """Should raise 404 when medication doesn't exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_medication_access(
                    mock_db, TEST_USER_ID, TEST_MEDICATION_ID
                )

        assert exc_info.value.status_code == 404


class TestVerifyDoseAccess:
    """Tests for verify_dose_access function."""

    @pytest.mark.asyncio
    async def test_verify_dose_access_success(self):
        """Should return dose when user has access."""
        mock_db = AsyncMock()
        mock_dose = create_mock_dose()
        mock_medication = create_mock_medication()
        mock_pet = create_mock_pet()
        mock_membership = create_mock_membership()

        # Mock the chain: dose -> medication -> pet -> membership
        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_dose)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_medication)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_pet)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_membership)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_dose_access(
                mock_db, TEST_USER_ID, TEST_DOSE_ID
            )

        assert result == mock_dose

    @pytest.mark.asyncio
    async def test_verify_dose_access_not_found(self):
        """Should raise 404 when dose doesn't exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_dose_access(mock_db, TEST_USER_ID, TEST_DOSE_ID)

        assert exc_info.value.status_code == 404


class TestVerifyFeedingAccess:
    """Tests for verify_feeding_access function."""

    @pytest.mark.asyncio
    async def test_verify_feeding_access_success(self):
        """Should return feeding when user has access."""
        mock_db = AsyncMock()
        mock_feeding = create_mock_feeding()
        mock_pet = create_mock_pet()
        mock_membership = create_mock_membership()

        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_feeding)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_pet)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_membership)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_feeding_access(
                mock_db, TEST_USER_ID, TEST_FEEDING_ID
            )

        assert result == mock_feeding

    @pytest.mark.asyncio
    async def test_verify_feeding_access_not_found(self):
        """Should raise 404 when feeding doesn't exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_feeding_access(
                    mock_db, TEST_USER_ID, TEST_FEEDING_ID
                )

        assert exc_info.value.status_code == 404


class TestVerifyHealthEventAccess:
    """Tests for verify_health_event_access function."""

    @pytest.mark.asyncio
    async def test_verify_health_event_access_success(self):
        """Should return health event when user has access."""
        mock_db = AsyncMock()
        mock_event = create_mock_event()
        mock_pet = create_mock_pet()
        mock_membership = create_mock_membership()

        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_event)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_pet)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_membership)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_health_event_access(
                mock_db, TEST_USER_ID, TEST_EVENT_ID
            )

        assert result == mock_event

    @pytest.mark.asyncio
    async def test_verify_health_event_access_not_found(self):
        """Should raise 404 when health event doesn't exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_health_event_access(
                    mock_db, TEST_USER_ID, TEST_EVENT_ID
                )

        assert exc_info.value.status_code == 404


class TestVerifyFoodAccess:
    """Tests for verify_food_access function."""

    @pytest.mark.asyncio
    async def test_verify_food_access_success(self):
        """Should return food when user has access."""
        mock_db = AsyncMock()
        mock_food = create_mock_food()
        mock_membership = create_mock_membership()

        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_food)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_membership)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_food_access(
                mock_db, TEST_USER_ID, TEST_FOOD_ID
            )

        assert result == mock_food

    @pytest.mark.asyncio
    async def test_verify_food_access_not_found(self):
        """Should raise 404 when food doesn't exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_food_access(mock_db, TEST_USER_ID, TEST_FOOD_ID)

        assert exc_info.value.status_code == 404
        assert "Food not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_food_access_wrong_family(self):
        """Should raise 403 when user doesn't have access to food's family."""
        mock_db = AsyncMock()
        mock_food = create_mock_food()

        # First call returns food, second returns no membership
        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_food)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_food_access(mock_db, TEST_USER_ID, TEST_FOOD_ID)

        assert exc_info.value.status_code == 403


class TestVerifyCalorieGoalAccess:
    """Tests for verify_calorie_goal_access function."""

    @pytest.mark.asyncio
    async def test_verify_calorie_goal_access_success(self):
        """Should return calorie goal when user has access."""
        mock_db = AsyncMock()
        mock_goal = create_mock_calorie_goal()
        mock_pet = create_mock_pet()
        mock_membership = create_mock_membership()

        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_goal)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_pet)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_membership)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_calorie_goal_access(
                mock_db, TEST_USER_ID, TEST_CALORIE_GOAL_ID
            )

        assert result == mock_goal

    @pytest.mark.asyncio
    async def test_verify_calorie_goal_access_not_found(self):
        """Should raise 404 when calorie goal doesn't exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_calorie_goal_access(
                    mock_db, TEST_USER_ID, TEST_CALORIE_GOAL_ID
                )

        assert exc_info.value.status_code == 404
        assert "Calorie goal not found" in str(exc_info.value.detail)


class TestVerifyHealthCategoryAccess:
    """Tests for verify_health_category_access function."""

    @pytest.mark.asyncio
    async def test_verify_health_category_access_success(self):
        """Should return health category when user has access."""
        mock_db = AsyncMock()
        mock_category = create_mock_health_category()
        mock_membership = create_mock_membership()

        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_category)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_membership)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            result = await verify_health_category_access(
                mock_db, TEST_USER_ID, TEST_HEALTH_CATEGORY_ID
            )

        assert result == mock_category

    @pytest.mark.asyncio
    async def test_verify_health_category_access_not_found(self):
        """Should raise 404 when health category doesn't exist."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_health_category_access(
                    mock_db, TEST_USER_ID, TEST_HEALTH_CATEGORY_ID
                )

        assert exc_info.value.status_code == 404
        assert "Health category not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_health_category_access_wrong_family(self):
        """Should raise 403 when user doesn't have access to category's family."""
        mock_db = AsyncMock()
        mock_category = create_mock_health_category()

        # First call returns category, second returns no membership
        mock_results = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_category)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ]
        mock_db.execute.side_effect = mock_results

        with patch("app.core.authorization.set_rls_user"):
            with pytest.raises(HTTPException) as exc_info:
                await verify_health_category_access(
                    mock_db, TEST_USER_ID, TEST_HEALTH_CATEGORY_ID
                )

        assert exc_info.value.status_code == 403
