"""
Tests for Pet Pydantic schemas.
"""
from datetime import date, datetime
from uuid import uuid4

import pytest

from app.schemas.pet import PetCreate, PetUpdate, PetResponse


class TestPetCreate:
    """Tests for PetCreate schema."""

    def test_create_with_required_fields_only(self):
        """Should create pet with only required fields."""
        pet = PetCreate(name="Buddy", kind="dog")

        assert pet.name == "Buddy"
        assert pet.kind == "dog"
        assert pet.photo_url is None
        assert pet.current_weight is None
        assert pet.date_of_birth is None

    def test_create_with_all_fields(self):
        """Should create pet with all fields including date_of_birth."""
        dob = date(2022, 3, 15)
        pet = PetCreate(
            name="Max",
            kind="cat",
            photo_url="https://example.com/photo.jpg",
            current_weight=10.5,
            date_of_birth=dob,
        )

        assert pet.name == "Max"
        assert pet.kind == "cat"
        assert pet.photo_url == "https://example.com/photo.jpg"
        assert pet.current_weight == 10.5
        assert pet.date_of_birth == dob

    def test_create_with_date_of_birth(self):
        """Should accept date_of_birth field."""
        dob = date(2020, 6, 1)
        pet = PetCreate(name="Luna", kind="dog", date_of_birth=dob)

        assert pet.date_of_birth == date(2020, 6, 1)

    def test_create_without_date_of_birth(self):
        """Should allow None for date_of_birth."""
        pet = PetCreate(name="Rocky", kind="hamster")

        assert pet.date_of_birth is None

    def test_create_with_iso8601_datetime_string(self):
        """Should parse ISO8601 datetime string (from iOS) to date."""
        pet = PetCreate(
            name="Max",
            kind="dog",
            date_of_birth="2022-03-15T00:00:00Z",
        )

        assert pet.date_of_birth == date(2022, 3, 15)

    def test_create_with_date_string(self):
        """Should parse date string (YYYY-MM-DD) to date."""
        pet = PetCreate(
            name="Luna",
            kind="cat",
            date_of_birth="2021-06-15",
        )

        assert pet.date_of_birth == date(2021, 6, 15)


class TestPetUpdate:
    """Tests for PetUpdate schema."""

    def test_update_all_none(self):
        """Should allow all fields to be None."""
        update = PetUpdate()

        assert update.name is None
        assert update.kind is None
        assert update.photo_url is None
        assert update.current_weight is None
        assert update.date_of_birth is None

    def test_update_date_of_birth_only(self):
        """Should allow updating only date_of_birth."""
        dob = date(2021, 12, 25)
        update = PetUpdate(date_of_birth=dob)

        assert update.name is None
        assert update.kind is None
        assert update.date_of_birth == dob

    def test_update_multiple_fields(self):
        """Should allow updating multiple fields including date_of_birth."""
        dob = date(2019, 8, 10)
        update = PetUpdate(
            name="Updated Name",
            current_weight=15.0,
            date_of_birth=dob,
        )

        assert update.name == "Updated Name"
        assert update.current_weight == 15.0
        assert update.date_of_birth == dob

    def test_update_with_iso8601_datetime_string(self):
        """Should parse ISO8601 datetime string (from iOS) to date."""
        update = PetUpdate(date_of_birth="2020-12-25T08:30:00Z")

        assert update.date_of_birth == date(2020, 12, 25)

    def test_update_with_date_string(self):
        """Should parse date string (YYYY-MM-DD) to date."""
        update = PetUpdate(date_of_birth="2019-04-20")

        assert update.date_of_birth == date(2019, 4, 20)


class TestPetResponse:
    """Tests for PetResponse schema."""

    def test_response_includes_date_of_birth(self):
        """Should include date_of_birth in response."""
        pet_id = uuid4()
        org_id = uuid4()
        dob = date(2022, 1, 1)

        response = PetResponse(
            id=pet_id,
            org_id=org_id,
            name="Whiskers",
            kind="cat",
            photo_url=None,
            current_weight=8.0,
            date_of_birth=dob,
            created_at=datetime.utcnow(),
            created_by=None,
        )

        assert response.date_of_birth == dob
        assert response.name == "Whiskers"

    def test_response_with_null_date_of_birth(self):
        """Should handle None date_of_birth in response."""
        pet_id = uuid4()
        org_id = uuid4()

        response = PetResponse(
            id=pet_id,
            org_id=org_id,
            name="Buddy",
            kind="dog",
            photo_url=None,
            current_weight=None,
            date_of_birth=None,
            created_at=datetime.utcnow(),
            created_by=None,
        )

        assert response.date_of_birth is None
