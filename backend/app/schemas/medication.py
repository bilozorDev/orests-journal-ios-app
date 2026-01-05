from datetime import UTC, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.models.medication import MedicationType


# Schedule Schemas
class ScheduledTimeCreate(BaseModel):
    hour: int  # 0-23
    minute: int = 0  # 0-59


class ScheduledTimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    scheduled_hour: int
    scheduled_minute: int


# Photo Schemas
class MedicationPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    photo_url: str
    sort_order: int
    created_at: datetime


# Medication Schemas
class MedicationCreate(BaseModel):
    pet_id: UUID
    name: str  # Full medical name (e.g., "fluticasone propionate")
    friendly_name: Optional[str] = None  # Short name for notifications (e.g., "Asthma inhaler")
    medication_type: MedicationType
    dosage: Optional[str] = None
    interval_days: Optional[int] = None  # 1-30 for scheduled, None for PRN
    is_as_needed: bool = False
    start_date: datetime
    end_date: Optional[datetime] = None
    times_per_day: int = 1
    notes: Optional[str] = None
    reminders_enabled: bool = False
    timezone: str = "UTC"
    scheduled_times: Optional[list[ScheduledTimeCreate]] = None  # Optional: set reminder times


class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    friendly_name: Optional[str] = None
    medication_type: Optional[MedicationType] = None
    dosage: Optional[str] = None
    interval_days: Optional[int] = None
    is_as_needed: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    times_per_day: Optional[int] = None
    notes: Optional[str] = None
    reminders_enabled: Optional[bool] = None
    timezone: Optional[str] = None
    scheduled_times: Optional[list[ScheduledTimeCreate]] = None


class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    name: str  # Full medical name
    friendly_name: Optional[str] = None  # Short name for notifications/widget
    medication_type: MedicationType
    dosage: Optional[str] = None
    interval_days: Optional[int] = None
    is_as_needed: bool = False
    start_date: datetime
    end_date: Optional[datetime] = None
    times_per_day: int
    notes: Optional[str] = None
    reminders_enabled: bool = False
    timezone: str = "UTC"
    is_archived: bool = False
    created_by: Optional[UUID] = None
    created_at: datetime

    @property
    def display_name(self) -> str:
        """Returns friendly_name if set, otherwise name."""
        return self.friendly_name or self.name

    @property
    def is_active(self) -> bool:
        """Check if medication is currently active."""
        now = datetime.now(UTC)
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class MedicationWithSchedulesResponse(MedicationResponse):
    """Medication response including scheduled reminder times and photos."""
    scheduled_times: list[ScheduledTimeResponse] = []
    photos: list[MedicationPhotoResponse] = []


class MedicationListItemResponse(MedicationResponse):
    """Medication with scheduled times for list responses (without photos for efficiency)."""
    scheduled_times: list[ScheduledTimeResponse] = []


class MedicationListResponse(BaseModel):
    medications: list[MedicationListItemResponse]
    total: int = 0


# Dose Schemas
class DoseCreate(BaseModel):
    medication_id: UUID
    notes: Optional[str] = None
    given_at: Optional[datetime] = None  # Defaults to now
    scheduled_for: Optional[datetime] = None  # Links dose to specific schedule slot


class DoseUpdate(BaseModel):
    given_at: Optional[datetime] = None
    given_by: Optional[UUID] = None
    notes: Optional[str] = None
    scheduled_for: Optional[datetime] = None


class DoseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    given_at: datetime
    given_by: UUID
    scheduled_for: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


class DoseDetailResponse(BaseModel):
    """Dose response with formatted user name instead of UUID."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    given_at: datetime
    given_by: str  # Formatted user name
    scheduled_for: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


class DoseListResponse(BaseModel):
    doses: list[DoseDetailResponse]
    total: int = 0  # Total count for pagination


class MedicationDeleteResponse(BaseModel):
    """Response from deleting/archiving a medication."""
    deleted: bool
    archived: bool
    message: str


class AllDoseDetailResponse(BaseModel):
    """Dose response with medication info for all-doses endpoint."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    medication_name: str
    pet_id: UUID
    given_at: datetime
    given_by: str
    scheduled_for: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime


class AllDosesListResponse(BaseModel):
    """Response for all-doses endpoint with pagination."""
    doses: list[AllDoseDetailResponse]
    total: int
