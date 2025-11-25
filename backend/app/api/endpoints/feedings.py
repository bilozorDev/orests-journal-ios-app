from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.pet import Pet
from app.models.food import PetFeeding, PetCalorieGoal
from app.schemas.food import (
    FeedingCreate, FeedingResponse, FeedingListResponse,
    CalorieGoalCreate, CalorieGoalResponse,
)

router = APIRouter()


@router.post("", response_model=FeedingResponse, status_code=status.HTTP_201_CREATED)
async def create_feeding(
    feeding_in: FeedingCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Record a pet feeding."""
    # Verify pet exists
    pet_query = select(Pet).where(Pet.id == feeding_in.pet_id)
    result = await db.execute(pet_query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    feeding = PetFeeding(
        pet_id=feeding_in.pet_id,
        food_id=feeding_in.food_id,
        fed_by=user_id,
        fed_at=feeding_in.fed_at or datetime.utcnow(),
        amount=feeding_in.amount,
        amount_unit=feeding_in.amount_unit.value,
        calories=feeding_in.calories,
        notes=feeding_in.notes,
    )
    db.add(feeding)
    await db.commit()
    await db.refresh(feeding)

    return FeedingResponse.model_validate(feeding)


@router.get("/pet/{pet_id}", response_model=FeedingListResponse)
async def list_pet_feedings(
    pet_id: UUID,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List feedings for a pet."""
    query = (
        select(PetFeeding)
        .where(PetFeeding.pet_id == pet_id)
        .order_by(PetFeeding.fed_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    feedings = result.scalars().all()

    total_calories = sum(f.calories for f in feedings)

    return FeedingListResponse(
        feedings=[FeedingResponse.model_validate(f) for f in feedings],
        total_calories=total_calories,
    )


@router.get("/pet/{pet_id}/today", response_model=FeedingListResponse)
async def get_today_feedings(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get today's feedings and calorie total for a pet."""
    # Get start of today (UTC)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    query = (
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
    result = await db.execute(query)
    feedings = result.scalars().all()

    total_calories = sum(f.calories for f in feedings)

    return FeedingListResponse(
        feedings=[FeedingResponse.model_validate(f) for f in feedings],
        total_calories=total_calories,
    )


@router.delete("/{feeding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feeding(
    feeding_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a feeding record."""
    query = select(PetFeeding).where(PetFeeding.id == feeding_id)
    result = await db.execute(query)
    feeding = result.scalar_one_or_none()

    if not feeding:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feeding not found",
        )

    await db.delete(feeding)
    await db.commit()


# Calorie Goals
@router.get("/pet/{pet_id}/calorie-goal", response_model=Optional[CalorieGoalResponse])
async def get_active_calorie_goal(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get the active calorie goal for a pet."""
    now = datetime.utcnow()

    query = (
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
    result = await db.execute(query)
    goal = result.scalar_one_or_none()

    if not goal:
        return None

    # Check if goal is still effective
    if goal.effective_until and goal.effective_until < now:
        return None

    return CalorieGoalResponse.model_validate(goal)


@router.post("/pet/{pet_id}/calorie-goal", response_model=CalorieGoalResponse, status_code=status.HTTP_201_CREATED)
async def set_calorie_goal(
    pet_id: UUID,
    goal_in: CalorieGoalCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Set a new calorie goal for a pet."""
    # Verify pet exists
    pet_query = select(Pet).where(Pet.id == pet_id)
    result = await db.execute(pet_query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    # Optionally: End previous goal
    now = datetime.utcnow()
    prev_goal_query = (
        select(PetCalorieGoal)
        .where(
            and_(
                PetCalorieGoal.pet_id == pet_id,
                PetCalorieGoal.effective_until.is_(None),
            )
        )
    )
    result = await db.execute(prev_goal_query)
    prev_goal = result.scalar_one_or_none()

    if prev_goal:
        prev_goal.effective_until = now

    # Create new goal
    goal = PetCalorieGoal(
        pet_id=pet_id,
        daily_calories=goal_in.daily_calories,
        effective_from=now,
        notes=goal_in.notes,
        created_by=user_id,
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    return CalorieGoalResponse.model_validate(goal)
