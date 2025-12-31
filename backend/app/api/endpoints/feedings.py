from datetime import datetime, timedelta, UTC
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.core.authorization import verify_pet_access, verify_feeding_access
from app.models.pet import Pet
from app.models.food import PetFeeding, PetCalorieGoal
from app.schemas.food import (
    FeedingCreate, FeedingUpdate, FeedingResponse, FeedingListResponse,
    CalorieGoalCreate, CalorieGoalResponse,
)
from app.cache.helpers import cache_get, cache_set, cache_delete_pattern
from app.cache.keys import key_feeding_history, TTL_FEEDING_HISTORY

router = APIRouter()


async def invalidate_feeding_caches(pet_id: UUID) -> None:
    """Invalidate all feeding-related caches for a pet."""
    # Invalidate dashboard and feeding history caches
    await cache_delete_pattern(f"dashboard:{pet_id}:*")
    await cache_delete_pattern(f"feeding_history:{pet_id}:*")


@router.post("", response_model=FeedingResponse, status_code=status.HTTP_201_CREATED)
async def create_feeding(
    feeding_in: FeedingCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Record a pet feeding."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, feeding_in.pet_id)

    feeding = PetFeeding(
        pet_id=feeding_in.pet_id,
        food_id=feeding_in.food_id,
        fed_by=UUID(user_id),
        fed_at=feeding_in.fed_at or datetime.now(UTC).replace(tzinfo=None),
        amount=feeding_in.amount,
        amount_unit=feeding_in.amount_unit.value,
        calories=feeding_in.calories,
        notes=feeding_in.notes,
    )
    db.add(feeding)
    await db.commit()
    await db.refresh(feeding)

    # Invalidate dashboard cache
    await invalidate_feeding_caches(feeding_in.pet_id)

    return FeedingResponse.model_validate(feeding)


@router.get("/pet/{pet_id}", response_model=FeedingListResponse)
async def list_pet_feedings(
    pet_id: UUID,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List feedings for a pet with pagination support."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    # Try cache first
    cache_key = key_feeding_history(str(pet_id), offset, limit)
    cached = await cache_get(cache_key, FeedingListResponse)
    if cached:
        return cached

    # Get total count for pagination
    count_query = select(func.count(PetFeeding.id)).where(PetFeeding.pet_id == pet_id)
    total = (await db.execute(count_query)).scalar() or 0

    # Get paginated feedings
    query = (
        select(PetFeeding)
        .where(PetFeeding.pet_id == pet_id)
        .order_by(PetFeeding.fed_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    feedings = result.scalars().all()

    total_calories = sum(f.calories for f in feedings)

    response = FeedingListResponse(
        feedings=[FeedingResponse.model_validate(f) for f in feedings],
        total_calories=total_calories,
        total=total,
    )

    # Cache the response
    await cache_set(cache_key, response, TTL_FEEDING_HISTORY)

    return response


@router.get("/pet/{pet_id}/today", response_model=FeedingListResponse)
async def get_today_feedings(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get today's feedings and calorie total for a pet."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    # Get start of today (UTC)
    today = datetime.now(UTC).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
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
    # Verify user has access to this feeding through family membership
    feeding = await verify_feeding_access(db, user_id, feeding_id)
    pet_id = feeding.pet_id

    await db.delete(feeding)
    await db.commit()

    # Invalidate dashboard cache
    await invalidate_feeding_caches(pet_id)


@router.patch("/{feeding_id}", response_model=FeedingResponse)
async def update_feeding(
    feeding_id: UUID,
    feeding_in: FeedingUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a feeding record."""
    # Verify user has access to this feeding through family membership
    feeding = await verify_feeding_access(db, user_id, feeding_id)

    update_data = feeding_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Convert enum values to their string values
        if field == 'amount_unit' and value is not None:
            value = value.value if hasattr(value, 'value') else value
        setattr(feeding, field, value)

    await db.commit()
    await db.refresh(feeding)

    # Invalidate dashboard cache
    await invalidate_feeding_caches(feeding.pet_id)

    return FeedingResponse.model_validate(feeding)


# Calorie Goals
@router.get("/pet/{pet_id}/calorie-goal", response_model=Optional[CalorieGoalResponse])
async def get_active_calorie_goal(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get the active calorie goal for a pet."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    now = datetime.now(UTC).replace(tzinfo=None)

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
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    # Optionally: End previous goal
    now = datetime.now(UTC).replace(tzinfo=None)
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
        created_by=UUID(user_id),
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    # Invalidate dashboard cache
    await invalidate_feeding_caches(pet_id)

    return CalorieGoalResponse.model_validate(goal)
