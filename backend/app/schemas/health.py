from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


# Health Category Schemas
class HealthCategoryCreate(BaseModel):
    name: str


class HealthCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    name: str
    name_normalized: str
    created_at: datetime


# Health Event Schemas
class HealthEventCreate(BaseModel):
    category_name: str  # Will get or create category
    occurred_at: Optional[datetime] = None  # Defaults to now
    notes: Optional[str] = None


class HealthEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    occurred_at: datetime
    notes: Optional[str] = None
    created_at: datetime


class HealthEventWithCategory(BaseModel):
    """Health event with its category details."""
    id: UUID
    category_id: UUID
    category_name: str
    occurred_at: datetime
    notes: Optional[str] = None
    created_at: datetime


class HealthEventListResponse(BaseModel):
    events: list[HealthEventWithCategory]
