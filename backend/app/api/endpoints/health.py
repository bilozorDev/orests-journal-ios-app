from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.core.authorization import verify_pet_access, verify_health_event_access
from app.models.pet import Pet
from app.models.health import PetHealthCategory, PetHealthEvent
from app.schemas.health import (
    HealthCategoryResponse,
    HealthEventCreate, HealthEventResponse, HealthEventListResponse,
    HealthEventWithCategory, HealthEventNested,
)

router = APIRouter()


# Categories
@router.get("/pet/{pet_id}/categories", response_model=list[HealthCategoryResponse])
async def list_categories(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List health categories for a pet."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

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
        created_by=UUID(user_id),
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
    user_id: str = Depends(get_current_user_id),
):
    """Create a health event for a pet."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    # Get or create category
    category = await get_or_create_category(
        db, pet_id, event_in.category_name, user_id
    )

    # Create event
    # Strip timezone info to avoid naive/aware datetime mixing
    occurred_at = event_in.occurred_at
    if occurred_at is not None and occurred_at.tzinfo is not None:
        occurred_at = occurred_at.replace(tzinfo=None)

    event = PetHealthEvent(
        category_id=category.id,
        occurred_at=occurred_at or datetime.utcnow(),
        notes=event_in.notes if event_in.notes else None,
        created_by=UUID(user_id),
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
    user_id: str = Depends(get_current_user_id),
):
    """List health events for a pet with their categories."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

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

    # Combine with category info (nested structure for iOS)
    events_with_category = []
    for event in events:
        category = categories.get(event.category_id)
        if category:
            events_with_category.append(
                HealthEventWithCategory(
                    event=HealthEventNested.model_validate(event),
                    category=HealthCategoryResponse.model_validate(category),
                )
            )

    return HealthEventListResponse(events=events_with_category)


@router.get("/events/{event_id}", response_model=HealthEventWithCategory)
async def get_health_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific health event with its category."""
    # Verify user has access to this event through family membership
    event = await verify_health_event_access(db, user_id, event_id)

    # Get event with category for response
    query = (
        select(PetHealthEvent, PetHealthCategory)
        .join(PetHealthCategory, PetHealthEvent.category_id == PetHealthCategory.id)
        .where(PetHealthEvent.id == event_id)
    )
    result = await db.execute(query)
    row = result.one()  # Event verified to exist by verify_health_event_access
    event, category = row

    return HealthEventWithCategory(
        event=HealthEventNested.model_validate(event),
        category=HealthCategoryResponse.model_validate(category),
    )


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a health event."""
    # Verify user has access to this event through family membership
    event = await verify_health_event_access(db, user_id, event_id)

    await db.delete(event)
    await db.commit()
