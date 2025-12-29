"""
Tests for Medication Pydantic schemas.

Validates medication schema behavior to prevent breaking changes to iOS app.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.medication import (
    MedicationCreate,
    MedicationUpdate,
    MedicationResponse,
    MedicationWithSchedulesResponse,
    ScheduledTimeCreate,
    ScheduledTimeResponse,
    MedicationPhotoResponse,
    DoseCreate,
    DoseResponse,
    DoseDetailResponse,
    AllDoseDetailResponse,
)
from app.models.medication import MedicationType


class TestMedicationType:
    """Tests for MedicationType enum."""

    def test_medication_type_all_values_valid(self):
        """All 8 medication types should be valid."""
        valid_types = [
            "drops", "pill", "inhaler", "shot",
            "liquid", "tablet", "capsule", "topical"
        ]

        for med_type in valid_types:
            # Should not raise
            result = MedicationType(med_type)
            assert result.value == med_type

    def test_medication_type_invalid_value_raises_error(self):
        """Invalid medication type should raise ValueError."""
        with pytest.raises(ValueError):
            MedicationType("invalid_type")

    def test_medication_type_case_sensitive(self):
        """Medication types are case-sensitive."""
        with pytest.raises(ValueError):
            MedicationType("PILL")  # Must be lowercase

    def test_medication_type_enum_count(self):
        """Should have exactly 8 medication types."""
        assert len(MedicationType) == 8


class TestMedicationCreate:
    """Tests for MedicationCreate schema."""

    def test_medication_create_required_fields_only(self):
        """Should create medication with only required fields."""
        med = MedicationCreate(
            pet_id=uuid4(),
            name="Prednisone",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
        )

        assert med.pet_id is not None
        assert med.name == "Prednisone"
        assert med.medication_type == MedicationType.PILL
        assert med.dosage is None
        assert med.interval_days is None
        assert med.is_as_needed is False  # Default
        assert med.times_per_day == 1  # Default
        assert med.reminders_enabled is False  # Default
        assert med.timezone == "UTC"  # Default

    def test_medication_create_with_all_fields(self):
        """Should create medication with all optional fields."""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30)

        med = MedicationCreate(
            pet_id=uuid4(),
            name="Prednisone",
            medication_type=MedicationType.PILL,
            dosage="5mg",
            interval_days=7,
            is_as_needed=False,
            start_date=start_date,
            end_date=end_date,
            times_per_day=2,
            notes="Give with food",
            reminders_enabled=True,
            timezone="America/New_York",
            scheduled_times=[
                ScheduledTimeCreate(hour=8, minute=0),
                ScheduledTimeCreate(hour=20, minute=0),
            ],
        )

        assert med.dosage == "5mg"
        assert med.interval_days == 7
        assert med.end_date == end_date
        assert med.times_per_day == 2
        assert med.notes == "Give with food"
        assert med.reminders_enabled is True
        assert med.timezone == "America/New_York"
        assert len(med.scheduled_times) == 2

    def test_medication_create_interval_days_valid_range(self):
        """Interval days should accept values 1-30."""
        for days in [1, 15, 30]:
            med = MedicationCreate(
                pet_id=uuid4(),
                name="Test",
                medication_type=MedicationType.PILL,
                start_date=datetime.utcnow(),
                interval_days=days,
            )
            assert med.interval_days == days

    def test_medication_create_interval_days_none_for_prn(self):
        """PRN (as-needed) medications should allow null interval_days."""
        med = MedicationCreate(
            pet_id=uuid4(),
            name="PRN Med",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            is_as_needed=True,
            interval_days=None,
        )

        assert med.is_as_needed is True
        assert med.interval_days is None

    def test_medication_create_times_per_day_defaults_to_one(self):
        """Times per day should default to 1."""
        med = MedicationCreate(
            pet_id=uuid4(),
            name="Test",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
        )

        assert med.times_per_day == 1

    def test_medication_create_scheduled_times_optional(self):
        """Scheduled times should be optional."""
        med = MedicationCreate(
            pet_id=uuid4(),
            name="Test",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            scheduled_times=None,
        )

        assert med.scheduled_times is None


class TestScheduledTimeCreate:
    """Tests for ScheduledTimeCreate schema."""

    def test_scheduled_time_create_valid_hour_and_minute(self):
        """Should accept valid hour (0-23) and minute (0-59)."""
        time = ScheduledTimeCreate(hour=14, minute=30)
        assert time.hour == 14
        assert time.minute == 30

    def test_scheduled_time_create_minute_defaults_to_zero(self):
        """Minute should default to 0."""
        time = ScheduledTimeCreate(hour=8)
        assert time.minute == 0

    def test_scheduled_time_create_boundary_values(self):
        """Should accept boundary values for hour and minute."""
        # Minimum values
        time1 = ScheduledTimeCreate(hour=0, minute=0)
        assert time1.hour == 0
        assert time1.minute == 0

        # Maximum values
        time2 = ScheduledTimeCreate(hour=23, minute=59)
        assert time2.hour == 23
        assert time2.minute == 59


class TestMedicationUpdate:
    """Tests for MedicationUpdate schema."""

    def test_medication_update_all_fields_optional(self):
        """All fields in update schema should be optional."""
        update = MedicationUpdate()

        assert update.name is None
        assert update.medication_type is None
        assert update.dosage is None
        assert update.interval_days is None
        assert update.is_as_needed is None
        assert update.start_date is None
        assert update.end_date is None
        assert update.times_per_day is None
        assert update.notes is None
        assert update.reminders_enabled is None
        assert update.timezone is None
        assert update.scheduled_times is None

    def test_medication_update_single_field(self):
        """Should allow updating a single field."""
        update = MedicationUpdate(name="Updated Name")

        assert update.name == "Updated Name"
        assert update.dosage is None  # Other fields remain None

    def test_medication_update_multiple_fields(self):
        """Should allow updating multiple fields."""
        update = MedicationUpdate(
            name="Updated Med",
            dosage="10mg",
            times_per_day=3,
        )

        assert update.name == "Updated Med"
        assert update.dosage == "10mg"
        assert update.times_per_day == 3

    def test_medication_update_scheduled_times(self):
        """Should allow updating scheduled times."""
        update = MedicationUpdate(
            scheduled_times=[
                ScheduledTimeCreate(hour=9, minute=0),
                ScheduledTimeCreate(hour=21, minute=0),
            ]
        )

        assert len(update.scheduled_times) == 2
        assert update.scheduled_times[0].hour == 9
        assert update.scheduled_times[1].hour == 21


class TestMedicationResponse:
    """Tests for MedicationResponse schema."""

    def test_medication_response_required_fields(self):
        """Response should require all non-nullable fields."""
        # This should not raise
        response = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Test Med",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            times_per_day=1,
            created_at=datetime.utcnow(),
        )

        assert response.id is not None
        assert response.name == "Test Med"

    def test_medication_response_is_active_property_before_start(self):
        """Medication should not be active before start date."""
        future_start = datetime.utcnow() + timedelta(days=7)

        response = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Future Med",
            medication_type=MedicationType.PILL,
            start_date=future_start,
            times_per_day=1,
            created_at=datetime.utcnow(),
        )

        assert response.is_active is False

    def test_medication_response_is_active_property_after_end(self):
        """Medication should not be active after end date."""
        past_start = datetime.utcnow() - timedelta(days=30)
        past_end = datetime.utcnow() - timedelta(days=1)

        response = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Ended Med",
            medication_type=MedicationType.PILL,
            start_date=past_start,
            end_date=past_end,
            times_per_day=1,
            created_at=datetime.utcnow(),
        )

        assert response.is_active is False

    def test_medication_response_is_active_property_ongoing(self):
        """Medication should be active when started and no end date."""
        past_start = datetime.utcnow() - timedelta(days=7)

        response = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Active Med",
            medication_type=MedicationType.PILL,
            start_date=past_start,
            end_date=None,
            times_per_day=1,
            created_at=datetime.utcnow(),
        )

        assert response.is_active is True

    def test_medication_response_is_active_property_within_range(self):
        """Medication should be active between start and end dates."""
        past_start = datetime.utcnow() - timedelta(days=7)
        future_end = datetime.utcnow() + timedelta(days=7)

        response = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Active Med",
            medication_type=MedicationType.PILL,
            start_date=past_start,
            end_date=future_end,
            times_per_day=1,
            created_at=datetime.utcnow(),
        )

        assert response.is_active is True

    def test_medication_response_defaults(self):
        """Response should include default values."""
        response = MedicationResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Test",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            times_per_day=1,
            created_at=datetime.utcnow(),
        )

        assert response.is_as_needed is False
        assert response.reminders_enabled is False
        assert response.timezone == "UTC"
        assert response.is_archived is False


class TestMedicationWithSchedulesResponse:
    """Tests for MedicationWithSchedulesResponse schema."""

    def test_medication_with_schedules_includes_times(self):
        """Response should include nested scheduled times."""
        med_id = uuid4()

        response = MedicationWithSchedulesResponse(
            id=med_id,
            pet_id=uuid4(),
            name="Test Med",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            times_per_day=2,
            created_at=datetime.utcnow(),
            scheduled_times=[
                ScheduledTimeResponse(
                    id=uuid4(),
                    medication_id=med_id,
                    scheduled_hour=8,
                    scheduled_minute=0,
                ),
                ScheduledTimeResponse(
                    id=uuid4(),
                    medication_id=med_id,
                    scheduled_hour=20,
                    scheduled_minute=0,
                ),
            ],
        )

        assert len(response.scheduled_times) == 2
        assert response.scheduled_times[0].scheduled_hour == 8
        assert response.scheduled_times[1].scheduled_hour == 20

    def test_medication_with_schedules_includes_photos(self):
        """Response should include nested photos."""
        med_id = uuid4()

        response = MedicationWithSchedulesResponse(
            id=med_id,
            pet_id=uuid4(),
            name="Test Med",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            times_per_day=1,
            created_at=datetime.utcnow(),
            photos=[
                MedicationPhotoResponse(
                    id=uuid4(),
                    medication_id=med_id,
                    photo_url="https://example.com/1.jpg",
                    sort_order=0,
                    created_at=datetime.utcnow(),
                ),
                MedicationPhotoResponse(
                    id=uuid4(),
                    medication_id=med_id,
                    photo_url="https://example.com/2.jpg",
                    sort_order=1,
                    created_at=datetime.utcnow(),
                ),
            ],
        )

        assert len(response.photos) == 2
        assert response.photos[0].sort_order == 0
        assert response.photos[1].sort_order == 1

    def test_medication_with_schedules_empty_lists(self):
        """Response should handle empty schedules and photos."""
        response = MedicationWithSchedulesResponse(
            id=uuid4(),
            pet_id=uuid4(),
            name="Test Med",
            medication_type=MedicationType.PILL,
            start_date=datetime.utcnow(),
            times_per_day=1,
            created_at=datetime.utcnow(),
            scheduled_times=[],
            photos=[],
        )

        assert response.scheduled_times == []
        assert response.photos == []


class TestDoseSchemas:
    """Tests for Dose-related schemas."""

    def test_dose_create_defaults_given_at_to_none(self):
        """DoseCreate should default given_at to None (will use now in endpoint)."""
        dose = DoseCreate(
            medication_id=uuid4(),
            notes="Took with breakfast",
        )

        assert dose.given_at is None
        assert dose.notes == "Took with breakfast"

    def test_dose_create_with_custom_timestamp(self):
        """DoseCreate should accept custom given_at timestamp."""
        past_time = datetime.utcnow() - timedelta(hours=2)

        dose = DoseCreate(
            medication_id=uuid4(),
            given_at=past_time,
        )

        assert dose.given_at == past_time

    def test_dose_response_fields(self):
        """DoseResponse should include all required fields."""
        dose = DoseResponse(
            id=uuid4(),
            medication_id=uuid4(),
            given_at=datetime.utcnow(),
            given_by=uuid4(),
            notes="Test notes",
            created_at=datetime.utcnow(),
        )

        assert dose.id is not None
        assert dose.given_by is not None
        assert dose.notes == "Test notes"

    def test_dose_detail_response_formatted_user_name(self):
        """DoseDetailResponse should have formatted user name instead of UUID."""
        dose = DoseDetailResponse(
            id=uuid4(),
            medication_id=uuid4(),
            given_at=datetime.utcnow(),
            given_by="You",  # Formatted name, not UUID
            notes=None,
            created_at=datetime.utcnow(),
        )

        assert dose.given_by == "You"
        assert isinstance(dose.given_by, str)

    def test_all_dose_detail_includes_medication_info(self):
        """AllDoseDetailResponse should include medication and pet info."""
        dose = AllDoseDetailResponse(
            id=uuid4(),
            medication_id=uuid4(),
            medication_name="Prednisone",
            pet_id=uuid4(),
            given_at=datetime.utcnow(),
            given_by="John Doe",
            notes=None,
            created_at=datetime.utcnow(),
        )

        assert dose.medication_name == "Prednisone"
        assert dose.pet_id is not None
