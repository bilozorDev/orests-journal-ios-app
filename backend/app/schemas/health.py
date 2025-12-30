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
    family_id: UUID
    name: str
    name_normalized: str
    created_at: datetime
    created_by: Optional[UUID] = None


# Health Event Schemas
class HealthEventCreate(BaseModel):
    category_name: str  # Will get or create category
    occurred_at: Optional[datetime] = None  # Defaults to now
    duration_minutes: Optional[int] = None  # Optional duration for behavioral events
    notes: Optional[str] = None
    notify_family: bool = False  # Send push notification to family members


class HealthEventUpdate(BaseModel):
    category_name: Optional[str] = None
    occurred_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None


# Health Event Photo Schemas
class HealthEventPhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    photo_url: str
    sort_order: int
    created_at: datetime


class HealthEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    occurred_at: datetime
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    photos: list[HealthEventPhotoResponse] = []
    created_at: datetime


class HealthEventNested(BaseModel):
    """Health event for nested response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    category_id: UUID
    occurred_at: datetime
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    photos: list[HealthEventPhotoResponse] = []
    created_at: datetime
    created_by: Optional[UUID] = None


class HealthEventWithCategory(BaseModel):
    """Health event with its category details (nested structure for iOS)."""
    event: HealthEventNested
    category: HealthCategoryResponse


class HealthEventListResponse(BaseModel):
    events: list[HealthEventWithCategory]


class HealthCategoryListResponse(BaseModel):
    """Wrapper for caching category list."""
    categories: list[HealthCategoryResponse]
