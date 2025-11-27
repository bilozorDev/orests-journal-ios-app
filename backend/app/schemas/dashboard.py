from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.schemas.food import FoodResponse, CalorieGoalResponse
from app.schemas.medication import MedicationResponse
from app.models.food import ContainerUnit


class DashboardFeedingResponse(BaseModel):
    """Feeding response for dashboard with formatted user name."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pet_id: UUID
    food_id: UUID
    fed_by: str  # Formatted user name instead of UUID
    fed_at: datetime
    amount: float
    amount_unit: ContainerUnit
    calories: float
    notes: Optional[str] = None
    created_at: datetime


class DashboardDoseResponse(BaseModel):
    """Dose response for dashboard with formatted user name."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    medication_id: UUID
    given_at: datetime
    given_by: str  # Formatted user name instead of UUID
    notes: Optional[str] = None
    created_at: datetime


class MedicationWithDoses(BaseModel):
    """Medication with dose information for dashboard display."""
    medication: MedicationResponse
    last_dose: Optional[DashboardDoseResponse] = None
    today_dose_count: int
    doses_remaining: int


class DashboardResponse(BaseModel):
    """Combined dashboard data for a pet in a single response."""
    calorie_goal: Optional[CalorieGoalResponse] = None
    today_feedings: list[DashboardFeedingResponse]
    total_calories: float
    foods: list[FoodResponse]
    medications: list[MedicationWithDoses]
