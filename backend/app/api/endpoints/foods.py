from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.food import PetFood, PetFeeding
from app.schemas.food import FoodCreate, FoodUpdate, FoodResponse, FoodListResponse, FoodDeleteResponse

router = APIRouter()


@router.get("", response_model=FoodListResponse)
async def list_foods(
    org_id: str,
    include_archived: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all foods for the organization (family)."""
    query = select(PetFood).where(PetFood.org_id == org_id)
    if not include_archived:
        query = query.where(PetFood.is_archived == False)
    query = query.order_by(PetFood.created_at.desc())
    result = await db.execute(query)
    foods = result.scalars().all()

    return FoodListResponse(foods=[FoodResponse.model_validate(f) for f in foods])


@router.post("", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
async def create_food(
    food_in: FoodCreate,
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new food item for the organization (family)."""
    food = PetFood(
        org_id=org_id,
        name=food_in.name,
        category=food_in.category.value,
        calories_per_kg=food_in.calories_per_kg,
        container_size=food_in.container_size,
        container_size_unit=food_in.container_size_unit.value,
        image_url=food_in.image_url,
        created_by=user_id,
    )
    db.add(food)
    await db.commit()
    await db.refresh(food)

    return FoodResponse.model_validate(food)


@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(
    food_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific food item by ID."""
    query = select(PetFood).where(PetFood.id == food_id)
    result = await db.execute(query)
    food = result.scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found",
        )

    return FoodResponse.model_validate(food)


@router.patch("/{food_id}", response_model=FoodResponse)
async def update_food(
    food_id: UUID,
    food_in: FoodUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a food item."""
    query = select(PetFood).where(PetFood.id == food_id)
    result = await db.execute(query)
    food = result.scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found",
        )

    update_data = food_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Convert enum values to their string values
        if field in ('category', 'container_size_unit') and value is not None:
            value = value.value if hasattr(value, 'value') else value
        setattr(food, field, value)

    await db.commit()
    await db.refresh(food)

    return FoodResponse.model_validate(food)


@router.delete("/{food_id}", response_model=FoodDeleteResponse)
async def delete_food(
    food_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete or archive a food item based on feeding history."""
    query = select(PetFood).where(PetFood.id == food_id)
    result = await db.execute(query)
    food = result.scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found",
        )

    # Check if food has any feedings
    feeding_count_query = select(func.count()).select_from(PetFeeding).where(PetFeeding.food_id == food_id)
    feeding_count_result = await db.execute(feeding_count_query)
    feeding_count = feeding_count_result.scalar()

    if feeding_count > 0:
        # Archive instead of delete to preserve feeding history
        food.is_archived = True
        await db.commit()
        return FoodDeleteResponse(
            deleted=False,
            archived=True,
            message=f"Food has {feeding_count} feeding record(s). It has been archived instead of deleted to preserve history."
        )
    else:
        # Hard delete since no feeding records exist
        await db.delete(food)
        await db.commit()
        return FoodDeleteResponse(
            deleted=True,
            archived=False,
            message="Food deleted successfully."
        )
