"""
Comprehensive integration tests for dashboard endpoints.

Tests cover:
- GET /api/v1/dashboard/pet/{pet_id} - Get dashboard data

Test scenarios:
- Happy path with data (medications, feedings, calorie goal)
- Happy path with empty data
- Timezone handling
- Unauthorized (401)
- Forbidden (403)
- Not found (404)
- Cache behavior
- User name formatting ("You" vs formatted name)
"""
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID

import pytest
from httpx import AsyncClient

from tests.conftest import (
    TEST_FAMILY_ID,
    TEST_USER_ID,
    create_mock_membership,
    create_mock_pet,
    create_mock_feeding,
    create_mock_calorie_goal,
    create_mock_food,
    create_mock_user,
)


# ============== Helper Functions ==============

def create_mock_medication(
    medication_id: str = None,
    pet_id: str = None,
    name: str = "Prednisone",
    medication_type: str = "pill",
    dosage: str = "5mg",
    start_date: datetime = None,
    end_date: datetime = None,
    times_per_day: int = 2,
    is_as_needed: bool = False,
):
    """Create a mock PetMedication object."""
    from types import SimpleNamespace
    medication = SimpleNamespace()
    medication.id = UUID(medication_id) if medication_id else uuid4()
    medication.pet_id = UUID(pet_id) if pet_id else uuid4()
    medication.name = name
    medication.medication_type = medication_type
    medication.dosage = dosage
    medication.start_date = start_date if start_date is not None else datetime.utcnow().date()
    medication.end_date = end_date  # Can be None
    medication.times_per_day = times_per_day
    medication.is_as_needed = is_as_needed
    medication.created_at = datetime.utcnow()
    medication.notes = None  # Add default notes field
    medication.photo_urls = []  # Add default photo_urls field
    return medication


def create_mock_dose(
    dose_id: str = None,
    medication_id: str = None,
    given_at: datetime = None,
    given_by: str = None,
    notes: str = None,
):
    """Create a mock PetMedicationDose object."""
    from types import SimpleNamespace
    dose = SimpleNamespace()
    dose.id = UUID(dose_id) if dose_id else uuid4()
    dose.medication_id = UUID(medication_id) if medication_id else uuid4()
    dose.given_at = given_at if given_at is not None else datetime.utcnow()
    dose.given_by = UUID(given_by) if given_by else uuid4()
    dose.notes = notes
    dose.created_at = datetime.utcnow()
    return dose


def create_mock_feeding_dashboard(
    pet_id: str = None,
    food_id: str = None,
    fed_by: str = None,
    fed_at: datetime = None,
    amount: float = 100.0,
    amount_unit: str = "g",
    calories: float = 350.0,
    notes: str = None,
):
    """Create a mock PetFeeding object for dashboard tests with proper UUID handling."""
    from types import SimpleNamespace
    feeding = SimpleNamespace()
    feeding.id = UUID(str(uuid4()))
    feeding.pet_id = UUID(pet_id) if pet_id else uuid4()
    feeding.food_id = UUID(food_id) if food_id else uuid4()
    # fed_by should be UUID object, not string
    feeding.fed_by = UUID(fed_by) if fed_by else uuid4()
    feeding.fed_at = fed_at if fed_at is not None else datetime.utcnow()
    feeding.amount = amount
    feeding.amount_unit = amount_unit
    feeding.calories = calories
    feeding.notes = notes
    feeding.created_at = datetime.utcnow()
    return feeding


def setup_dashboard_access_verification(
    mock_db_session: AsyncMock,
    mock_pet,
    mock_membership,
    additional_results=None,
):
    """
    Helper to set up db.execute mock with proper side_effect chain for dashboard access.

    Dashboard endpoint calls verify_pet_access which:
    1. Executes RLS SET LOCAL query (set_rls_user)
    2. Queries for the pet
    3. Calls verify_family_access which:
       a. Executes RLS SET LOCAL query (set_rls_user again)
       b. Queries for membership
    """
    results = []

    # RLS SET LOCAL #1 (from verify_pet_access calling set_rls_user)
    rls_result1 = MagicMock()
    rls_result1.scalar_one_or_none.return_value = None
    results.append(rls_result1)

    # Pet query (from verify_pet_access)
    pet_result = MagicMock()
    pet_result.scalar_one_or_none.return_value = mock_pet
    results.append(pet_result)

    # RLS SET LOCAL #2 (from verify_family_access calling set_rls_user)
    rls_result2 = MagicMock()
    rls_result2.scalar_one_or_none.return_value = None
    results.append(rls_result2)

    # Membership query (from verify_family_access)
    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = mock_membership
    results.append(membership_result)

    # Add any additional results for business logic queries
    if additional_results:
        results.extend(additional_results)

    mock_db_session.execute = AsyncMock(side_effect=results)


# ============== Dashboard Tests ==============

class TestGetDashboardData:
    """Tests for GET /api/v1/dashboard/pet/{pet_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_dashboard_success_with_data(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return complete dashboard data with feedings and medications."""
        pet_id = str(uuid4())
        food_id = str(uuid4())
        med_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock calorie goal
        mock_goal = create_mock_calorie_goal(
            pet_id=pet_id,
            daily_calories=500.0,
            effective_until=None,  # Active
        )
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = mock_goal

        # Mock today's feedings
        now = datetime.now(dt_timezone.utc).replace(tzinfo=None)
        mock_feeding = create_mock_feeding_dashboard(
            pet_id=pet_id,
            food_id=food_id,
            fed_by=test_user_id,
            fed_at=now,
            calories=200.0,
        )
        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = [mock_feeding]

        # Mock foods
        mock_food = create_mock_food(food_id=food_id, org_id=test_family_id)
        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = [mock_food]

        # Mock active medications
        mock_medication = create_mock_medication(
            medication_id=med_id,
            pet_id=pet_id,
            times_per_day=2,
        )
        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = [mock_medication]

        # Mock dose count for today
        dose_count_result = MagicMock()
        dose_count_row = MagicMock()
        dose_count_row.medication_id = UUID(med_id)
        dose_count_row.count = 1
        dose_count_result.__iter__ = lambda self: iter([dose_count_row])

        # Mock last dose
        mock_dose = create_mock_dose(
            medication_id=med_id,
            given_by=test_user_id,
            given_at=now - timedelta(hours=2),
        )
        last_dose_result = MagicMock()
        last_dose_result.scalars.return_value.all.return_value = [mock_dose]

        # Mock user lookup
        mock_user = create_mock_user(user_id=test_user_id, first_name="Test", last_name="User")
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
                dose_count_result,
                last_dose_result,
                users_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set") as mock_cache_set:

            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()

            # Verify calorie goal
            assert data["calorie_goal"] is not None
            assert data["calorie_goal"]["daily_calories"] == 500.0

            # Verify feedings
            assert len(data["today_feedings"]) == 1
            assert data["today_feedings"][0]["calories"] == 200.0
            assert data["today_feedings"][0]["fed_by"] == "You"  # Current user
            assert data["total_calories"] == 200.0

            # Verify foods
            assert len(data["foods"]) == 1

            # Verify medications
            assert len(data["medications"]) == 1
            med = data["medications"][0]
            assert med["medication"]["name"] == "Prednisone"
            assert med["today_dose_count"] == 1
            assert med["doses_remaining"] == 1  # 2 per day - 1 given = 1 remaining
            assert med["last_dose"] is not None
            assert med["last_dose"]["given_by"] == "You"

            # Verify cache was set
            mock_cache_set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_dashboard_empty_data(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return empty dashboard when pet has no data."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock no calorie goal
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        # Mock no feedings
        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        # Mock no foods
        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        # Mock no medications
        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = []

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["calorie_goal"] is None
            assert len(data["today_feedings"]) == 0
            assert data["total_calories"] == 0
            assert len(data["foods"]) == 0
            assert len(data["medications"]) == 0

    @pytest.mark.asyncio
    async def test_get_dashboard_expired_calorie_goal(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return null calorie goal when goal is expired."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock expired calorie goal
        now = datetime.now(dt_timezone.utc).replace(tzinfo=None)
        mock_goal = create_mock_calorie_goal(
            pet_id=pet_id,
            daily_calories=500.0,
            effective_until=now - timedelta(days=1),  # Expired yesterday
        )
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = mock_goal

        # Mock empty results for other queries
        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = []

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["calorie_goal"] is None  # Expired goal is not returned

    @pytest.mark.asyncio
    async def test_get_dashboard_formats_user_names(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should format user names as 'You' for current user and formatted name for others."""
        pet_id = str(uuid4())
        food_id = str(uuid4())
        other_user_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock no goal
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        # Mock two feedings: one by current user, one by other user
        now = datetime.now(dt_timezone.utc).replace(tzinfo=None)
        mock_feeding1 = create_mock_feeding_dashboard(
            pet_id=pet_id,
            food_id=food_id,
            fed_by=test_user_id,
            fed_at=now,
            calories=100.0,
        )
        mock_feeding2 = create_mock_feeding_dashboard(
            pet_id=pet_id,
            food_id=food_id,
            fed_by=other_user_id,
            fed_at=now - timedelta(hours=1),
            calories=150.0,
        )
        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = [mock_feeding1, mock_feeding2]

        # Mock foods
        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        # Mock no medications
        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = []

        # Mock users
        mock_user1 = create_mock_user(user_id=test_user_id, first_name="Test", last_name="User")
        mock_user2 = create_mock_user(user_id=other_user_id, first_name="Jane", last_name="Smith")
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user1, mock_user2]

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
                users_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["today_feedings"]) == 2

            # Find each feeding and check the fed_by format
            feeding_by_current_user = next(f for f in data["today_feedings"] if f["calories"] == 100.0)
            feeding_by_other_user = next(f for f in data["today_feedings"] if f["calories"] == 150.0)

            assert feeding_by_current_user["fed_by"] == "You"
            assert feeding_by_other_user["fed_by"] == "Jane S."  # Formatted name

    @pytest.mark.asyncio
    async def test_get_dashboard_medication_dose_calculation(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should correctly calculate doses remaining."""
        pet_id = str(uuid4())
        med_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock no goal, feedings, foods
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        # Mock medication that requires 3 doses per day
        mock_medication = create_mock_medication(
            medication_id=med_id,
            pet_id=pet_id,
            times_per_day=3,
        )
        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = [mock_medication]

        # Mock 2 doses given today
        dose_count_result = MagicMock()
        dose_count_row = MagicMock()
        dose_count_row.medication_id = UUID(med_id)
        dose_count_row.count = 2
        dose_count_result.__iter__ = lambda self: iter([dose_count_row])

        # Mock last dose
        mock_dose = create_mock_dose(medication_id=med_id, given_by=test_user_id)
        last_dose_result = MagicMock()
        last_dose_result.scalars.return_value.all.return_value = [mock_dose]

        # Mock user
        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
                dose_count_result,
                last_dose_result,
                users_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["medications"]) == 1
            med = data["medications"][0]
            assert med["today_dose_count"] == 2
            assert med["doses_remaining"] == 1  # 3 per day - 2 given = 1 remaining

    @pytest.mark.asyncio
    async def test_get_dashboard_timezone_handling(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should handle timezone parameter correctly."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock empty results
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = []

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request with timezone parameter
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}&timezone=America/Los_Angeles",
                headers=auth_headers,
            )

            # Verify response (should not error with valid timezone)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_dashboard_invalid_timezone_fallback(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should fallback to UTC for invalid timezone."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock empty results
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = []

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request with invalid timezone
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}&timezone=Invalid/Timezone",
                headers=auth_headers,
            )

            # Should not error, should fallback to UTC
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_dashboard_cache_hit(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should return cached data when available."""
        pet_id = str(uuid4())

        # Mock access verification (still needed for security check)
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # RLS query #1 (verify_pet_access)
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query (returns the pet)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query #2 (verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # Membership query
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = mock_membership

        mock_db_session.execute = AsyncMock(side_effect=[rls_result1, pet_result, rls_result2, membership_result])

        # Mock cached response
        cached_data = {
            "calorie_goal": None,
            "today_feedings": [],
            "total_calories": 0,
            "foods": [],
            "medications": [],
        }

        with patch("app.api.endpoints.dashboard.cache_get", return_value=cached_data):
            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response came from cache
            assert response.status_code == 200
            data = response.json()
            assert data == cached_data

    @pytest.mark.asyncio
    async def test_get_dashboard_without_auth(
        self,
        client: AsyncClient,
    ):
        """Should return 401 when no auth token provided."""
        pet_id = str(uuid4())

        response = await client.get(
            f"/api/v1/dashboard/pet/{pet_id}?org_id={TEST_FAMILY_ID}",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_dashboard_no_access(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
    ):
        """Should return 403 when user doesn't have access to pet."""
        pet_id = str(uuid4())
        other_family_id = str(uuid4())

        # Pet exists but user has no access
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=other_family_id)

        # RLS query #1 (verify_pet_access)
        rls_result1 = MagicMock()
        rls_result1.scalar_one_or_none.return_value = None

        # Pet query (returns the pet)
        pet_result = MagicMock()
        pet_result.scalar_one_or_none.return_value = mock_pet

        # RLS query #2 (verify_family_access)
        rls_result2 = MagicMock()
        rls_result2.scalar_one_or_none.return_value = None

        # No membership
        membership_result = MagicMock()
        membership_result.scalar_one_or_none.return_value = None

        mock_db_session.execute = AsyncMock(side_effect=[rls_result1, pet_result, rls_result2, membership_result])

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None):
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={other_family_id}",
                headers=auth_headers,
            )

            assert response.status_code == 403
            assert "not a member" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_dashboard_invalid_pet_uuid(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 for invalid pet_id UUID."""
        response = await client.get(
            f"/api/v1/dashboard/pet/not-a-uuid?org_id={TEST_FAMILY_ID}",
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_dashboard_missing_org_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Should return 422 when org_id parameter is missing."""
        pet_id = str(uuid4())

        response = await client.get(
            f"/api/v1/dashboard/pet/{pet_id}",
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_dashboard_cache_control_header(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should include Cache-Control header for client-side caching."""
        pet_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock empty results
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = []

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify Cache-Control header
            assert response.status_code == 200
            assert "Cache-Control" in response.headers
            assert "private" in response.headers["Cache-Control"]
            assert "max-age=60" in response.headers["Cache-Control"]
            assert "stale-while-revalidate=300" in response.headers["Cache-Control"]

    @pytest.mark.asyncio
    async def test_get_dashboard_prn_medication_no_doses_remaining(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should handle PRN (as-needed) medications correctly."""
        pet_id = str(uuid4())
        med_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock empty results for goal, feedings, foods
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        # Mock PRN medication (times_per_day=1 for PRN)
        mock_medication = create_mock_medication(
            medication_id=med_id,
            pet_id=pet_id,
            is_as_needed=True,
            times_per_day=1,
        )
        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = [mock_medication]

        # Mock no doses given today
        dose_count_result = MagicMock()
        dose_count_result.__iter__ = lambda self: iter([])

        # Mock no last dose
        last_dose_result = MagicMock()
        last_dose_result.scalars.return_value.all.return_value = []

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
                dose_count_result,
                last_dose_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["medications"]) == 1
            med = data["medications"][0]
            assert med["today_dose_count"] == 0
            assert med["doses_remaining"] == 1
            assert med["last_dose"] is None

    @pytest.mark.asyncio
    async def test_get_dashboard_multiple_medications(
        self,
        client: AsyncClient,
        mock_db_session: AsyncMock,
        auth_headers: dict,
        test_user_id: str,
        test_family_id: str,
    ):
        """Should handle multiple medications with different dose counts."""
        pet_id = str(uuid4())
        med1_id = str(uuid4())
        med2_id = str(uuid4())

        # Mock access verification
        mock_pet = create_mock_pet(pet_id=pet_id, org_id=test_family_id)
        mock_membership = create_mock_membership(user_id=test_user_id, family_id=test_family_id)

        # Mock empty results for goal, feedings, foods
        goal_result = MagicMock()
        goal_result.scalar_one_or_none.return_value = None

        feedings_result = MagicMock()
        feedings_result.scalars.return_value.all.return_value = []

        foods_result = MagicMock()
        foods_result.scalars.return_value.all.return_value = []

        # Mock two medications
        mock_med1 = create_mock_medication(
            medication_id=med1_id,
            pet_id=pet_id,
            name="Med A",
            times_per_day=2,
        )
        mock_med2 = create_mock_medication(
            medication_id=med2_id,
            pet_id=pet_id,
            name="Med B",
            times_per_day=3,
        )
        meds_result = MagicMock()
        meds_result.scalars.return_value.all.return_value = [mock_med1, mock_med2]

        # Mock dose counts
        dose_count_result = MagicMock()
        row1 = MagicMock()
        row1.medication_id = UUID(med1_id)
        row1.count = 1
        row2 = MagicMock()
        row2.medication_id = UUID(med2_id)
        row2.count = 3  # All doses given
        dose_count_result.__iter__ = lambda self: iter([row1, row2])

        # Mock last doses
        dose1 = create_mock_dose(medication_id=med1_id, given_by=test_user_id)
        dose2 = create_mock_dose(medication_id=med2_id, given_by=test_user_id)
        last_dose_result = MagicMock()
        last_dose_result.scalars.return_value.all.return_value = [dose1, dose2]

        # Mock user
        mock_user = create_mock_user(user_id=test_user_id)
        users_result = MagicMock()
        users_result.scalars.return_value.all.return_value = [mock_user]

        setup_dashboard_access_verification(
            mock_db_session,
            mock_pet,
            mock_membership,
            additional_results=[
                goal_result,
                feedings_result,
                foods_result,
                meds_result,
                dose_count_result,
                last_dose_result,
                users_result,
            ]
        )

        # Mock cache miss
        with patch("app.api.endpoints.dashboard.cache_get", return_value=None), \
             patch("app.api.endpoints.dashboard.cache_set"):

            # Make request
            response = await client.get(
                f"/api/v1/dashboard/pet/{pet_id}?org_id={test_family_id}",
                headers=auth_headers,
            )

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data["medications"]) == 2

            # Find each medication and verify
            med_a = next(m for m in data["medications"] if m["medication"]["name"] == "Med A")
            med_b = next(m for m in data["medications"] if m["medication"]["name"] == "Med B")

            assert med_a["today_dose_count"] == 1
            assert med_a["doses_remaining"] == 1  # 2 - 1 = 1

            assert med_b["today_dose_count"] == 3
            assert med_b["doses_remaining"] == 0  # 3 - 3 = 0
