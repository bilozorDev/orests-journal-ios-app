from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.models.food import FoodCategory, ContainerUnit


# Food Schemas
class FoodCreate(BaseModel):
    name: str
    category: FoodCategory
    calories_per_kg: float
    container_size: float
    container_size_unit: ContainerUnit = ContainerUnit.GRAMS
    image_url: Optional[str] = None


class FoodUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[FoodCategory] = None
    calories_per_kg: Optional[float] = None
    container_size: Optional[float] = None
    container_size_unit: Optional[ContainerUnit] = None
    image_url: Optional[str] = None


class FoodResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    family_id: UUID
    name: str
    category: FoodCategory
    calories_per_kg: float
    container_size: float
    container_size_unit: ContainerUnit
    image_url: Optional[str] = None
    is_archived: bool = False
    created_at: datetime


class FoodListResponse(BaseModel):
    foods: list[FoodResponse]


class FoodDeleteResponse(BaseModel):
    deleted: bool
    archived: bool
    message: str


# Feeding Schemas
class FeedingCreate(BaseModel):
    pet_id: UUID
    food_id: UUID
    amount: float
    amount_unit: ContainerUnit = ContainerUnit.GRAMS
    calories: float
    notes: Optional[str] = None
    fed_at: Optional[datetime] = None  # Defaults to now


class FeedingUpdate(BaseModel):
    amount: Optional[float] = None
    amount_unit: Optional[ContainerUnit] = None
    calories: Optional[float] = None
    notes: Optional[str] = None
    fed_at: Optional[datetime] = None
    fed_by: Optional[UUID] = None


class FeedingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    food_id: UUID
    fed_by: UUID
    fed_at: datetime
    amount: float
    amount_unit: ContainerUnit
    calories: float
    notes: Optional[str] = None
    created_at: datetime


class FeedingListResponse(BaseModel):
    feedings: list[FeedingResponse]
    total_calories: float = 0
    total: int = 0  # Total count for pagination


# Calorie Goal Schemas
class CalorieGoalCreate(BaseModel):
    daily_calories: float
    notes: Optional[str] = None


class CalorieGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    daily_calories: float
    effective_from: datetime
    effective_until: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
