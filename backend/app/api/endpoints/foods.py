from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.food import PetFood
from app.schemas.food import FoodCreate, FoodUpdate, FoodResponse, FoodListResponse

router = APIRouter()


@router.get("", response_model=FoodListResponse)
async def list_foods(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all foods for the organization (family)."""
    query = select(PetFood).where(PetFood.org_id == org_id).order_by(PetFood.created_at.desc())
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
        category=food_in.category,
        calories_per_kg=food_in.calories_per_kg,
        container_size=food_in.container_size,
        container_size_unit=food_in.container_size_unit,
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
        setattr(food, field, value)

    await db.commit()
    await db.refresh(food)

    return FoodResponse.model_validate(food)


@router.delete("/{food_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_food(
    food_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a food item."""
    query = select(PetFood).where(PetFood.id == food_id)
    result = await db.execute(query)
    food = result.scalar_one_or_none()

    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food not found",
        )

    await db.delete(food)
    await db.commit()
