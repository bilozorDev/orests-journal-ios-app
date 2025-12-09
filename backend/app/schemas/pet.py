from datetime import datetime, date
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator


def parse_date_flexible(value):
    """Parse date from either date string or datetime string."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Try parsing as date first (YYYY-MM-DD)
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
        # Try parsing as datetime
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            pass
    raise ValueError(f"Cannot parse date from: {value}")


# Pet Schemas
class PetCreate(BaseModel):
    name: str
    kind: str
    photo_url: Optional[str] = None
    current_weight: Optional[float] = None
    date_of_birth: Optional[date] = None

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def parse_date_of_birth(cls, v):
        return parse_date_flexible(v)


class PetUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    photo_url: Optional[str] = None
    current_weight: Optional[float] = None
    date_of_birth: Optional[date] = None

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def parse_date_of_birth(cls, v):
        return parse_date_flexible(v)


class PetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    name: str
    kind: str
    photo_url: Optional[str] = None
    current_weight: Optional[float] = None
    date_of_birth: Optional[date] = None
    created_at: datetime
    created_by: Optional[UUID] = None


class PetListResponse(BaseModel):
    pets: list[PetResponse]


# Health Record Schemas
class HealthRecordCreate(BaseModel):
    age_years: Optional[float] = None
    weight_pounds: Optional[float] = None
    notes: Optional[str] = None


class HealthRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    age_years: Optional[float] = None
    weight_pounds: Optional[float] = None
    notes: Optional[str] = None
    recorded_at: datetime
