from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from app.schemas.food import FoodResponse, FeedingResponse, CalorieGoalResponse
from app.schemas.medication import MedicationResponse, DoseResponse


class MedicationWithDoses(BaseModel):
    """Medication with dose information for dashboard display."""
    medication: MedicationResponse
    last_dose: Optional[DoseResponse] = None
    today_dose_count: int
    doses_remaining: int


class DashboardResponse(BaseModel):
    """Combined dashboard data for a pet in a single response."""
    calorie_goal: Optional[CalorieGoalResponse] = None
    today_feedings: list[FeedingResponse]
    total_calories: float
    foods: list[FoodResponse]
    medications: list[MedicationWithDoses]
