from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import ClerkUser, get_current_user
from app.models.pet import Pet
from app.models.health import PetHealthCategory, PetHealthEvent
from app.schemas.health import (
    HealthCategoryResponse,
    HealthEventCreate, HealthEventResponse, HealthEventListResponse,
    HealthEventWithCategory,
)

router = APIRouter()


# Categories
@router.get("/pet/{pet_id}/categories", response_model=list[HealthCategoryResponse])
async def list_categories(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """List health categories for a pet."""
    query = (
        select(PetHealthCategory)
        .where(PetHealthCategory.pet_id == pet_id)
        .order_by(PetHealthCategory.name)
    )
    result = await db.execute(query)
    categories = result.scalars().all()

    return [HealthCategoryResponse.model_validate(c) for c in categories]


async def get_or_create_category(
    db: AsyncSession,
    pet_id: UUID,
    name: str,
    user_id: str,
) -> PetHealthCategory:
    """Get an existing category or create a new one."""
    normalized = name.lower().strip()

    # Try to find existing
    query = (
        select(PetHealthCategory)
        .where(
            PetHealthCategory.pet_id == pet_id,
            PetHealthCategory.name_normalized == normalized,
        )
        .limit(1)
    )
    result = await db.execute(query)
    category = result.scalar_one_or_none()

    if category:
        return category

    # Create new
    category = PetHealthCategory(
        pet_id=pet_id,
        name=name.strip(),
        name_normalized=normalized,
        created_by=user_id,
    )
    db.add(category)
    await db.flush()

    return category


# Events
@router.post("/pet/{pet_id}/events", response_model=HealthEventResponse, status_code=status.HTTP_201_CREATED)
async def create_health_event(
    pet_id: UUID,
    event_in: HealthEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Create a health event for a pet."""
    # Verify pet exists
    pet_query = select(Pet).where(Pet.id == pet_id)
    result = await db.execute(pet_query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    # Get or create category
    category = await get_or_create_category(
        db, pet_id, event_in.category_name, current_user.id
    )

    # Create event
    event = PetHealthEvent(
        category_id=category.id,
        occurred_at=event_in.occurred_at or datetime.utcnow(),
        notes=event_in.notes if event_in.notes else None,
        created_by=current_user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    return HealthEventResponse.model_validate(event)


@router.get("/pet/{pet_id}/events", response_model=HealthEventListResponse)
async def list_health_events(
    pet_id: UUID,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """List health events for a pet with their categories."""
    # Get categories for this pet
    cat_query = select(PetHealthCategory).where(PetHealthCategory.pet_id == pet_id)
    cat_result = await db.execute(cat_query)
    categories = {c.id: c for c in cat_result.scalars().all()}

    if not categories:
        return HealthEventListResponse(events=[])

    # Get events for these categories
    event_query = (
        select(PetHealthEvent)
        .where(PetHealthEvent.category_id.in_(categories.keys()))
        .order_by(PetHealthEvent.occurred_at.desc())
        .limit(limit)
    )
    event_result = await db.execute(event_query)
    events = event_result.scalars().all()

    # Combine with category info
    events_with_category = []
    for event in events:
        category = categories.get(event.category_id)
        if category:
            events_with_category.append(
                HealthEventWithCategory(
                    id=event.id,
                    category_id=event.category_id,
                    category_name=category.name,
                    occurred_at=event.occurred_at,
                    notes=event.notes,
                    created_at=event.created_at,
                )
            )

    return HealthEventListResponse(events=events_with_category)


@router.get("/events/{event_id}", response_model=HealthEventWithCategory)
async def get_health_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Get a specific health event with its category."""
    # Get event with category
    query = (
        select(PetHealthEvent, PetHealthCategory)
        .join(PetHealthCategory, PetHealthEvent.category_id == PetHealthCategory.id)
        .where(PetHealthEvent.id == event_id)
    )
    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health event not found",
        )

    event, category = row

    return HealthEventWithCategory(
        id=event.id,
        category_id=event.category_id,
        category_name=category.name,
        occurred_at=event.occurred_at,
        notes=event.notes,
        created_at=event.created_at,
    )


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Delete a health event."""
    query = select(PetHealthEvent).where(PetHealthEvent.id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health event not found",
        )

    await db.delete(event)
    await db.commit()
