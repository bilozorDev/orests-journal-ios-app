from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.models.medication import MedicationType


# Medication Schemas
class MedicationCreate(BaseModel):
    pet_id: UUID
    name: str
    medication_type: MedicationType
    start_date: datetime
    end_date: Optional[datetime] = None
    times_per_day: int = 1
    notes: Optional[str] = None


class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    medication_type: Optional[MedicationType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    times_per_day: Optional[int] = None
    notes: Optional[str] = None


class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    name: str
    medication_type: MedicationType
    start_date: datetime
    end_date: Optional[datetime] = None
    times_per_day: int
    notes: Optional[str] = None
    created_at: datetime

    @property
    def is_active(self) -> bool:
        """Check if medication is currently active."""
        from datetime import datetime
        now = datetime.utcnow()
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        return True


class MedicationListResponse(BaseModel):
    medications: list[MedicationResponse]


# Dose Schemas
class DoseCreate(BaseModel):
    medication_id: UUID
    notes: Optional[str] = None
    given_at: Optional[datetime] = None  # Defaults to now


class DoseUpdate(BaseModel):
    given_at: Optional[datetime] = None
    given_by: Optional[UUID] = None
    notes: Optional[str] = None


class DoseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    given_at: datetime
    given_by: UUID
    notes: Optional[str] = None
    created_at: datetime


class DoseDetailResponse(BaseModel):
    """Dose response with formatted user name instead of UUID."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    given_at: datetime
    given_by: str  # Formatted user name
    notes: Optional[str] = None
    created_at: datetime


class DoseListResponse(BaseModel):
    doses: list[DoseDetailResponse]
