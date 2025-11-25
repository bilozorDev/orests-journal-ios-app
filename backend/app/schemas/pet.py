from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# Pet Schemas
class PetCreate(BaseModel):
    name: str
    kind: str
    photo_url: Optional[str] = None
    current_weight: Optional[float] = None


class PetUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    photo_url: Optional[str] = None
    current_weight: Optional[float] = None


class PetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: str
    name: str
    kind: str
    photo_url: Optional[str] = None
    current_weight: Optional[float] = None
    created_at: datetime
    created_by: Optional[str] = None


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
