"""
Test fixtures and configuration for pytest.
"""
import os
from datetime import datetime
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
    family = MagicMock()
    family.id = family_id
    family.name = name
    family.invite_code = invite_code
    family.created_at = datetime.utcnow()
    return family


# Helper to create mock membership
def create_mock_membership(
    user_id: str,
    family_id: str = TEST_FAMILY_ID,
    role: str = "member",
):
    """Create a mock FamilyMember object."""
    membership = MagicMock()
    membership.id = str(uuid4())
    membership.user_id = user_id
    membership.family_id = family_id
    membership.role = role
    membership.joined_at = datetime.utcnow()
    return membership


# Helper to create mock pet
def create_mock_pet(
    pet_id: str = None,
    org_id: str = TEST_FAMILY_ID,
    name: str = "Buddy",
    kind: str = "dog",
    date_of_birth=None,
    photo_url: str = None,
    current_weight: float = None,
    created_by: str = None,
):
    """Create a mock Pet object."""
    pet = MagicMock()
    pet.id = pet_id or str(uuid4())
    pet.org_id = org_id
    pet.name = name
    pet.kind = kind
    pet.date_of_birth = date_of_birth
    pet.photo_url = photo_url
    pet.current_weight = current_weight
    pet.created_at = datetime.utcnow()
    pet.created_by = created_by
    return pet
