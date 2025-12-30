"""
Test fixtures and configuration for pytest.
"""
import os
from datetime import UTC, datetime
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Set test environment variables BEFORE importing app modules
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DEBUG"] = "true"

from app.core.security import create_access_token
from app.main import app
from app.db import get_db


# Test UUIDs
TEST_USER_ID = str(uuid4())
TEST_ADMIN_USER_ID = str(uuid4())
TEST_FAMILY_ID = str(uuid4())


@pytest.fixture
def test_user_id() -> str:
    """Return a test user ID."""
    return TEST_USER_ID


@pytest.fixture
def test_admin_user_id() -> str:
    """Return a test admin user ID."""
    return TEST_ADMIN_USER_ID


@pytest.fixture
def test_family_id() -> str:
    """Return a test family ID."""
    return TEST_FAMILY_ID


@pytest.fixture
def auth_headers(test_user_id: str) -> dict:
    """Create auth headers with a valid JWT token."""
    token = create_access_token(test_user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(test_admin_user_id: str) -> dict:
    """Create auth headers for an admin user."""
    token = create_access_token(test_admin_user_id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
async def client(mock_db_session: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with mocked database."""

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# Helper to create mock family
def create_mock_family(
    family_id: str = TEST_FAMILY_ID,
    name: str = "Test Family",
    invite_code: str = "ABC12345",
):
    """Create a mock Family object."""
    from uuid import UUID
    family = MagicMock()
    # Convert string to UUID if needed for proper comparisons
    if isinstance(family_id, str):
        family.id = UUID(family_id)
    else:
        family.id = family_id
    family.name = name
    family.invite_code = invite_code
    family.created_at = datetime.now(UTC)
    return family


# Helper to create mock membership
def create_mock_membership(
    user_id: str,
    family_id: str = None,
    role: str = "member",
):
    """Create a mock FamilyMember object."""
    from uuid import UUID
    membership = MagicMock()
    membership.id = uuid4()

    # Ensure proper UUID handling
    if isinstance(user_id, str):
        membership.user_id = UUID(user_id)
    else:
        membership.user_id = user_id

    if family_id:
        if isinstance(family_id, str):
            membership.family_id = UUID(family_id)
        else:
            membership.family_id = family_id
    else:
        membership.family_id = UUID(TEST_FAMILY_ID)

    membership.role = role
    membership.joined_at = datetime.now(UTC)
    return membership


# Helper to create mock pet
def create_mock_pet(
    pet_id: str = None,
    family_id: str = None,
    name: str = "Buddy",
    kind: str = "dog",
    date_of_birth=None,
    photo_url: str = None,
    current_weight: float = None,
    created_by: str = None,
):
    """Create a mock Pet object."""
    from uuid import UUID
    pet = MagicMock()

    # Ensure proper UUID handling - convert strings to UUID objects
    if pet_id:
        pet.id = UUID(pet_id) if isinstance(pet_id, str) else pet_id
    else:
        pet.id = uuid4()

    if family_id:
        pet.family_id = UUID(family_id) if isinstance(family_id, str) else family_id
    else:
        pet.family_id = UUID(TEST_FAMILY_ID)

    pet.name = name
    pet.kind = kind
    pet.date_of_birth = date_of_birth
    pet.photo_url = photo_url
    pet.current_weight = current_weight
    pet.created_at = datetime.now(UTC)

    if created_by:
        pet.created_by = UUID(created_by) if isinstance(created_by, str) else created_by
    else:
        pet.created_by = None

    return pet


# Helper to create mock food
def create_mock_food(
    food_id: str = None,
    family_id: str = TEST_FAMILY_ID,
    name: str = "Test Food",
    category: str = "dry",
    calories_per_kg: float = 3500.0,
    container_size: float = 1000.0,
    container_size_unit: str = "g",
    image_url: str = None,
    is_archived: bool = False,
    created_by: str = None,
):
    """Create a mock PetFood object."""
    from uuid import UUID
    from types import SimpleNamespace
    food = SimpleNamespace()
    # Ensure UUID objects
    food.id = UUID(food_id) if food_id else uuid4()
    food.family_id = UUID(family_id) if isinstance(family_id, str) else family_id
    food.name = name
    food.category = category
    food.calories_per_kg = calories_per_kg
    food.container_size = container_size
    food.container_size_unit = container_size_unit
    food.image_url = image_url
    food.is_archived = is_archived
    food.created_at = datetime.now(UTC)
    food.created_by = UUID(created_by) if created_by else None
    return food


# Helper to create mock feeding
def create_mock_feeding(
    feeding_id: str = None,
    pet_id: str = None,
    food_id: str = None,
    fed_by: str = TEST_USER_ID,
    fed_at: datetime = None,
    amount: float = 100.0,
    amount_unit: str = "g",
    calories: float = 350.0,
    notes: str = None,
):
    """Create a mock PetFeeding object."""
    feeding = MagicMock()
    feeding.id = feeding_id or str(uuid4())
    feeding.pet_id = pet_id or str(uuid4())
    feeding.food_id = food_id or str(uuid4())
    feeding.fed_by = fed_by
    feeding.fed_at = fed_at or datetime.now(UTC)
    feeding.amount = amount
    feeding.amount_unit = amount_unit
    feeding.calories = calories
    feeding.notes = notes
    feeding.created_at = datetime.now(UTC)
    return feeding


# Helper to create mock calorie goal
def create_mock_calorie_goal(
    goal_id: str = None,
    pet_id: str = None,
    daily_calories: float = 400.0,
    effective_from: datetime = None,
    effective_until: datetime = None,
    notes: str = None,
    created_by: str = TEST_USER_ID,
):
    """Create a mock PetCalorieGoal object."""
    from uuid import UUID
    from types import SimpleNamespace

    # Use SimpleNamespace instead of MagicMock to avoid comparison issues
    goal = SimpleNamespace()
    goal.id = UUID(goal_id) if goal_id else uuid4()
    goal.pet_id = UUID(pet_id) if pet_id else uuid4()
    goal.daily_calories = daily_calories
    goal.effective_from = effective_from if effective_from is not None else datetime.now(UTC)
    goal.effective_until = effective_until  # Can be None or datetime
    goal.notes = notes
    goal.created_by = UUID(created_by) if isinstance(created_by, str) else created_by
    goal.created_at = datetime.now(UTC)
    return goal


# Helper to create mock user
def create_mock_user(
    user_id: str = None,
    apple_user_id: str = "apple_123456",
    email: str = "test@example.com",
    first_name: str = "Test",
    last_name: str = "User",
):
    """Create a mock User object."""
    from uuid import UUID
    user = MagicMock()
    user.id = UUID(user_id) if user_id else uuid4()
    user.apple_user_id = apple_user_id
    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.created_at = datetime.now(UTC)
    return user
