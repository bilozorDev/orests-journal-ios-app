from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.pet import Pet
from app.models.food import PetFood, PetFeeding, PetCalorieGoal
from app.models.medication import PetMedication, PetMedicationDose
from app.schemas.food import FoodResponse, FeedingResponse, CalorieGoalResponse
from app.schemas.medication import MedicationResponse, DoseResponse
from app.schemas.dashboard import DashboardResponse, MedicationWithDoses

router = APIRouter()


@router.get("/pet/{pet_id}", response_model=DashboardResponse)
async def get_dashboard_data(
    pet_id: UUID,
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get all dashboard data for a pet in a single API call.

    This endpoint combines multiple queries to reduce the number of API calls
    from the client, eliminating the N+1 problem for medication doses.
    """
    # Verify pet exists and belongs to org
    pet_query = select(Pet).where(and_(Pet.id == pet_id, Pet.org_id == org_id))
    result = await db.execute(pet_query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    # 1. Get active calorie goal
    goal_query = (
        select(PetCalorieGoal)
        .where(
            and_(
                PetCalorieGoal.pet_id == pet_id,
                PetCalorieGoal.effective_from <= now,
            )
        )
        .order_by(PetCalorieGoal.effective_from.desc())
        .limit(1)
    )
    goal_result = await db.execute(goal_query)
    goal = goal_result.scalar_one_or_none()

    # Check if goal is still effective
    calorie_goal = None
    if goal and (not goal.effective_until or goal.effective_until >= now):
        calorie_goal = CalorieGoalResponse.model_validate(goal)

    # 2. Get today's feedings
    feedings_query = (
        select(PetFeeding)
        .where(
            and_(
                PetFeeding.pet_id == pet_id,
                PetFeeding.fed_at >= today,
                PetFeeding.fed_at < tomorrow,
            )
        )
        .order_by(PetFeeding.fed_at.desc())
    )
    feedings_result = await db.execute(feedings_query)
    feedings = feedings_result.scalars().all()

    today_feedings = [FeedingResponse.model_validate(f) for f in feedings]
    total_calories = sum(f.calories for f in feedings)

    # 3. Get foods for the org (for name lookup in UI)
    foods_query = (
        select(PetFood)
        .where(PetFood.org_id == org_id)
        .order_by(PetFood.created_at.desc())
    )
    foods_result = await db.execute(foods_query)
    foods = foods_result.scalars().all()
    foods_list = [FoodResponse.model_validate(f) for f in foods]

    # 4. Get active medications for this pet
    meds_query = (
        select(PetMedication)
        .where(
            and_(
                PetMedication.pet_id == pet_id,
                PetMedication.start_date <= now,
                or_(
                    PetMedication.end_date.is_(None),
                    PetMedication.end_date >= now,
                ),
            )
        )
        .order_by(PetMedication.created_at.desc())
    )
    meds_result = await db.execute(meds_query)
    medications = meds_result.scalars().all()

    # 5. Batch query: Get today's dose counts for all active medications
    med_ids = [m.id for m in medications]
    today_dose_counts = {}
    last_doses = {}

    if med_ids:
        # Get today's dose counts in one query
        dose_counts_query = (
            select(
                PetMedicationDose.medication_id,
                func.count(PetMedicationDose.id).label("count")
            )
            .where(
                and_(
                    PetMedicationDose.medication_id.in_(med_ids),
                    PetMedicationDose.given_at >= today,
                    PetMedicationDose.given_at < tomorrow,
                )
            )
            .group_by(PetMedicationDose.medication_id)
        )
        counts_result = await db.execute(dose_counts_query)
        for row in counts_result:
            today_dose_counts[row.medication_id] = row.count

        # Get last dose for each medication in one query using a subquery
        # We'll get all doses ordered by date and filter to get the latest per medication
        last_dose_subquery = (
            select(
                PetMedicationDose.medication_id,
                func.max(PetMedicationDose.given_at).label("max_given_at")
            )
            .where(PetMedicationDose.medication_id.in_(med_ids))
            .group_by(PetMedicationDose.medication_id)
            .subquery()
        )

        last_doses_query = (
            select(PetMedicationDose)
            .join(
                last_dose_subquery,
                and_(
                    PetMedicationDose.medication_id == last_dose_subquery.c.medication_id,
                    PetMedicationDose.given_at == last_dose_subquery.c.max_given_at,
                )
            )
        )
        last_doses_result = await db.execute(last_doses_query)
        for dose in last_doses_result.scalars().all():
            last_doses[dose.medication_id] = dose

    # Build medication responses with dose info
    medications_with_doses = []
    for med in medications:
        today_count = today_dose_counts.get(med.id, 0)
        doses_remaining = max(0, med.times_per_day - today_count)
        last_dose = last_doses.get(med.id)

        medications_with_doses.append(
            MedicationWithDoses(
                medication=MedicationResponse.model_validate(med),
                last_dose=DoseResponse.model_validate(last_dose) if last_dose else None,
                today_dose_count=today_count,
                doses_remaining=doses_remaining,
            )
        )

    return DashboardResponse(
        calorie_goal=calorie_goal,
        today_feedings=today_feedings,
        total_calories=total_calories,
        foods=foods_list,
        medications=medications_with_doses,
    )
