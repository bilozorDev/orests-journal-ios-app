import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.core.security import get_current_user_id
from app.core.authorization import verify_pet_access, verify_health_event_access
from app.models.pet import Pet
from app.models.health import PetHealthCategory, PetHealthEvent, PetHealthEventPhoto
from app.schemas.health import (
    HealthCategoryResponse,
    HealthEventCreate, HealthEventUpdate, HealthEventResponse, HealthEventListResponse,
    HealthEventWithCategory, HealthEventNested, HealthEventPhotoResponse,
)
from app.services.storage import storage_service
from app.services.apns import apns_service
from app.services.family_notifications import get_filtered_family_member_tokens

logger = logging.getLogger(__name__)

router = APIRouter()


def validate_photo_url(photo_url: Optional[str], org_id: str) -> Optional[str]:
    """Validate that a photo URL belongs to the expected R2 storage and org.

    Returns the validated URL or None if invalid/empty.
    Raises HTTPException if URL format is invalid.
    """
    if not photo_url:
        return None

    # Empty string signals photo removal
    if photo_url == "":
        return None

    # Check if storage is configured
    if not storage_service.is_configured:
        # Allow any URL if storage not configured (dev mode)
        return photo_url

    public_url_base = storage_service.settings.s3_public_url

    # Validate URL starts with our storage
    if not photo_url.startswith(public_url_base):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo URL: must be from our storage service"
        )

    # Extract and validate path: folder/org_id/filename
    path = photo_url.replace(f"{public_url_base}/", "")
    path_parts = path.split("/")

    if len(path_parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo URL format"
        )

    folder, url_org_id, filename = path_parts

    # Validate org_id matches (security check)
    if url_org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Photo URL belongs to a different organization"
        )

    return photo_url


async def notify_family_health_event(
    db: AsyncSession,
    org_id: UUID,
    exclude_user_id: UUID,
    pet_name: str,
    category_name: str,
) -> None:
    """Send push notification to other family members about a new health event.

    Args:
        db: Database session
        org_id: The family/org ID
        exclude_user_id: User who created the event (won't receive notification)
        pet_name: Name of the pet
        category_name: Name of the health category
    """
    # Use a generic notification type - we could add health_event_added to preferences later
    tokens = await get_filtered_family_member_tokens(db, org_id, exclude_user_id, "pet_updated")
    if not tokens:
        return

    await apns_service.send_to_multiple(
        device_tokens=tokens,
        title=f"Health Event: {pet_name}",
        body=f"{category_name} recorded",
        data={
            "type": "health_event_added",
            "family_id": str(org_id),
            "pet_name": pet_name,
            "category": category_name,
        },
    )


# Categories
@router.get("/pet/{pet_id}/categories", response_model=list[HealthCategoryResponse])
async def list_categories(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List health categories for a pet's family (categories are family-wide)."""
    # Verify user has access to this pet through family membership
    pet = await verify_pet_access(db, user_id, pet_id)

    # Categories are family-wide, filter by org_id
    query = (
        select(PetHealthCategory)
        .where(PetHealthCategory.org_id == pet.org_id)
        .order_by(PetHealthCategory.name)
    )
    result = await db.execute(query)
    categories = result.scalars().all()

    return [HealthCategoryResponse.model_validate(c) for c in categories]


async def delete_orphaned_category(db: AsyncSession, category_id: UUID) -> bool:
    """Delete a category if it has no events referencing it.

    Returns True if category was deleted, False otherwise.
    """
    # Count events using this category
    count_query = select(func.count(PetHealthEvent.id)).where(
        PetHealthEvent.category_id == category_id
    )
    result = await db.execute(count_query)
    event_count = result.scalar() or 0

    if event_count == 0:
        # Category is orphaned, delete it
        cat_query = select(PetHealthCategory).where(PetHealthCategory.id == category_id)
        cat_result = await db.execute(cat_query)
        category = cat_result.scalar_one_or_none()
        if category:
            await db.delete(category)
            logger.info(f"Deleted orphaned category: {category.name} (id={category_id})")
            return True
    return False


async def get_or_create_category(
    db: AsyncSession,
    org_id: UUID,
    name: str,
    user_id: str,
) -> PetHealthCategory:
    """Get an existing category or create a new one (categories are family-wide)."""
    normalized = name.lower().strip()

    # Try to find existing category in this family
    query = (
        select(PetHealthCategory)
        .where(
            PetHealthCategory.org_id == org_id,
            PetHealthCategory.name_normalized == normalized,
        )
        .limit(1)
    )
    result = await db.execute(query)
    category = result.scalar_one_or_none()

    if category:
        return category

    # Create new category for this family
    category = PetHealthCategory(
        org_id=org_id,
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
    pet = await verify_pet_access(db, user_id, pet_id)

    # Validate occurred_at is not in the future
    if event_in.occurred_at is not None:
        # Compare in UTC to handle timezone differences
        now_utc = datetime.now(timezone.utc)
        occurred_at_utc = event_in.occurred_at
        if occurred_at_utc.tzinfo is None:
            occurred_at_utc = occurred_at_utc.replace(tzinfo=timezone.utc)
        # Allow a small buffer (1 minute) for clock drift
        if occurred_at_utc > now_utc.replace(second=0, microsecond=0) + timedelta(minutes=1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Health event date cannot be in the future"
            )

    # Get or create category (categories are family-wide)
    category = await get_or_create_category(
        db, pet.org_id, event_in.category_name, user_id
    )

    # Create event
    # Strip timezone info to avoid naive/aware datetime mixing
    occurred_at = event_in.occurred_at
    if occurred_at is not None and occurred_at.tzinfo is not None:
        occurred_at = occurred_at.replace(tzinfo=None)

    event = PetHealthEvent(
        pet_id=pet_id,
        category_id=category.id,
        occurred_at=occurred_at or datetime.utcnow(),
        notes=event_in.notes if event_in.notes else None,
        created_by=UUID(user_id),
    )
    db.add(event)
    await db.commit()

    # Reload event with photos for response
    event_query = (
        select(PetHealthEvent)
        .options(selectinload(PetHealthEvent.photos))
        .where(PetHealthEvent.id == event.id)
    )
    event_result = await db.execute(event_query)
    event = event_result.scalar_one()

    # Send notification to family members if requested
    if event_in.notify_family:
        try:
            await notify_family_health_event(
                db, pet.org_id, UUID(user_id), pet.name, event_in.category_name
            )
        except Exception as e:
            # Don't fail the create if notification fails
            logger.error(f"Failed to send health event notification: {e}")

    return HealthEventResponse.model_validate(event)


@router.get("/pet/{pet_id}/events", response_model=HealthEventListResponse)
async def list_health_events(
    pet_id: UUID,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    category: Optional[str] = Query(default=None, description="Filter by category name (fuzzy match)"),
    since: Optional[datetime] = Query(default=None, description="Filter events after this datetime (ISO8601)"),
    until: Optional[datetime] = Query(default=None, description="Filter events before this datetime (ISO8601)"),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List health events for a pet with their categories.

    Supports filtering by:
    - category: Fuzzy match on category name (e.g., 'vomit' matches 'Vomit', 'vomiting')
    - since: Only return events that occurred after this datetime
    - until: Only return events that occurred before this datetime
    """
    # Verify user has access to this pet through family membership
    pet = await verify_pet_access(db, user_id, pet_id)

    # Get categories for this family (categories are family-wide)
    cat_query = select(PetHealthCategory).where(PetHealthCategory.org_id == pet.org_id)
    if category:
        # Fuzzy match: category name contains the search term
        cat_query = cat_query.where(
            PetHealthCategory.name_normalized.ilike(f"%{category.lower().strip()}%")
        )
    cat_result = await db.execute(cat_query)
    categories = {c.id: c for c in cat_result.scalars().all()}

    # Get events for this pet (with photos)
    event_query = (
        select(PetHealthEvent)
        .options(selectinload(PetHealthEvent.photos))
        .where(PetHealthEvent.pet_id == pet_id)
    )

    # Filter by category (fuzzy match)
    if category and categories:
        event_query = event_query.where(PetHealthEvent.category_id.in_(categories.keys()))
    elif category and not categories:
        # Category filter specified but no matching categories exist
        return HealthEventListResponse(events=[])

    # Filter by time range
    if since:
        # Strip timezone if present for comparison with naive datetimes in DB
        since_naive = since.replace(tzinfo=None) if since.tzinfo else since
        event_query = event_query.where(PetHealthEvent.occurred_at >= since_naive)
    if until:
        until_naive = until.replace(tzinfo=None) if until.tzinfo else until
        event_query = event_query.where(PetHealthEvent.occurred_at <= until_naive)

    event_query = (
        event_query
        .order_by(PetHealthEvent.occurred_at.desc())
        .offset(offset)
        .limit(limit)
    )
    event_result = await db.execute(event_query)
    events = event_result.scalars().all()

    # Combine with category info (nested structure for iOS)
    events_with_category = []
    for event in events:
        cat = categories.get(event.category_id)
        if cat:
            events_with_category.append(
                HealthEventWithCategory(
                    event=HealthEventNested.model_validate(event),
                    category=HealthCategoryResponse.model_validate(cat),
                )
            )

    return HealthEventListResponse(events=events_with_category)


@router.get("/pet/{pet_id}/search", response_model=HealthEventListResponse)
async def search_health_events(
    pet_id: UUID,
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = Query(default=None, description="Filter by category name"),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Search health events by keyword in notes and category names."""
    # Verify user has access to this pet through family membership
    pet = await verify_pet_access(db, user_id, pet_id)

    search_term = f"%{q.lower().strip()}%"

    # Get categories for this family (categories are family-wide)
    cat_query = select(PetHealthCategory).where(PetHealthCategory.org_id == pet.org_id)
    if category:
        cat_query = cat_query.where(PetHealthCategory.name_normalized == category.lower().strip())
    cat_result = await db.execute(cat_query)
    categories = {c.id: c for c in cat_result.scalars().all()}

    if not categories:
        return HealthEventListResponse(events=[])

    # Search events for this pet: match in notes OR category name
    matching_category_ids = [
        c_id for c_id, c in categories.items()
        if q.lower() in c.name_normalized
    ]

    event_query = (
        select(PetHealthEvent)
        .options(selectinload(PetHealthEvent.photos))
        .where(PetHealthEvent.pet_id == pet_id)
        .where(
            or_(
                func.lower(PetHealthEvent.notes).like(search_term),
                PetHealthEvent.category_id.in_(matching_category_ids) if matching_category_ids else False,
            )
        )
        .order_by(PetHealthEvent.occurred_at.desc())
        .offset(offset)
        .limit(limit)
    )
    event_result = await db.execute(event_query)
    events = event_result.scalars().all()

    # Combine with category info
    events_with_category = []
    for event in events:
        cat = categories.get(event.category_id)
        if cat:
            events_with_category.append(
                HealthEventWithCategory(
                    event=HealthEventNested.model_validate(event),
                    category=HealthCategoryResponse.model_validate(cat),
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

    # Get event with category and photos for response
    query = (
        select(PetHealthEvent, PetHealthCategory)
        .join(PetHealthCategory, PetHealthEvent.category_id == PetHealthCategory.id)
        .options(selectinload(PetHealthEvent.photos))
        .where(PetHealthEvent.id == event_id)
    )
    result = await db.execute(query)
    row = result.one()  # Event verified to exist by verify_health_event_access
    event, category = row

    return HealthEventWithCategory(
        event=HealthEventNested.model_validate(event),
        category=HealthCategoryResponse.model_validate(category),
    )


@router.patch("/events/{event_id}", response_model=HealthEventWithCategory)
async def update_health_event(
    event_id: UUID,
    event_in: HealthEventUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a health event."""
    # Verify user has access to this event through family membership
    event = await verify_health_event_access(db, user_id, event_id)

    # Get current category for potential update
    cat_query = select(PetHealthCategory).where(PetHealthCategory.id == event.category_id)
    cat_result = await db.execute(cat_query)
    current_category = cat_result.scalar_one()

    # Store old category_id in case we need to clean up orphaned category
    old_category_id = event.category_id if event_in.category_name is not None else None

    # Handle category change if provided (categories are family-wide)
    if event_in.category_name is not None:
        new_category = await get_or_create_category(
            db, current_category.org_id, event_in.category_name, user_id
        )
        event.category_id = new_category.id
        current_category = new_category

    # Update other fields
    if event_in.occurred_at is not None:
        occurred_at = event_in.occurred_at
        if occurred_at.tzinfo is not None:
            occurred_at = occurred_at.replace(tzinfo=None)
        event.occurred_at = occurred_at

    if event_in.notes is not None:
        event.notes = event_in.notes if event_in.notes else None

    await db.commit()

    # Clean up orphaned category if category was changed
    if old_category_id and old_category_id != event.category_id:
        await delete_orphaned_category(db, old_category_id)
        await db.commit()

    # Reload event with photos for response
    event_query = (
        select(PetHealthEvent)
        .options(selectinload(PetHealthEvent.photos))
        .where(PetHealthEvent.id == event_id)
    )
    event_result = await db.execute(event_query)
    event = event_result.scalar_one()

    return HealthEventWithCategory(
        event=HealthEventNested.model_validate(event),
        category=HealthCategoryResponse.model_validate(current_category),
    )


@router.post("/events/{event_id}/photo", response_model=HealthEventPhotoResponse)
async def upload_health_event_photo(
    event_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Upload a photo for a health event (appends to existing photos)."""
    # Verify user has access to this event through family membership
    event = await verify_health_event_access(db, user_id, event_id)

    # Check photo limit (max 3 photos per event)
    photo_count_query = select(func.count(PetHealthEventPhoto.id)).where(
        PetHealthEventPhoto.event_id == event_id
    )
    photo_count_result = await db.execute(photo_count_query)
    current_count = photo_count_result.scalar() or 0

    if current_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 3 photos per health event"
        )

    # Get pet for org_id (events have pet_id directly)
    pet_query = select(Pet).where(Pet.id == event.pet_id)
    pet_result = await db.execute(pet_query)
    pet = pet_result.scalar_one()

    # Upload photo to R2
    photo_url = await storage_service.upload_image(
        file=file,
        upload_type="health-event-photo",
        org_id=str(pet.org_id),
    )

    # Create photo record
    photo = PetHealthEventPhoto(
        event_id=event_id,
        photo_url=photo_url,
        sort_order=current_count,  # Append at end
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return HealthEventPhotoResponse.model_validate(photo)


@router.delete("/events/{event_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_event_photo(
    event_id: UUID,
    photo_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a specific photo from a health event."""
    # Verify user has access to this event through family membership
    await verify_health_event_access(db, user_id, event_id)

    # Get the photo
    photo_query = select(PetHealthEventPhoto).where(
        PetHealthEventPhoto.id == photo_id,
        PetHealthEventPhoto.event_id == event_id,
    )
    photo_result = await db.execute(photo_query)
    photo = photo_result.scalar_one_or_none()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    # Delete photo from R2
    try:
        deleted = await storage_service.delete_image(photo.photo_url)
        if deleted:
            logger.info(f"Deleted health event photo: {photo.photo_url}")
    except Exception as e:
        logger.error(f"Failed to delete health event photo from R2: {e}")

    # Delete photo record
    await db.delete(photo)
    await db.commit()


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_health_event(
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a health event."""
    # Verify user has access to this event through family membership
    event = await verify_health_event_access(db, user_id, event_id)

    # Store category_id before deletion for orphan cleanup
    category_id = event.category_id

    # Get all photos for this event
    photos_query = select(PetHealthEventPhoto).where(PetHealthEventPhoto.event_id == event_id)
    photos_result = await db.execute(photos_query)
    photos = photos_result.scalars().all()

    # Delete all photos from R2
    for photo in photos:
        try:
            deleted = await storage_service.delete_image(photo.photo_url)
            if deleted:
                logger.info(f"Deleted health event photo on event deletion: {photo.photo_url}")
        except Exception as e:
            logger.error(f"Failed to delete health event photo on event deletion: {e}")

    await db.delete(event)
    await db.commit()

    # Clean up orphaned category if this was the last event using it
    await delete_orphaned_category(db, category_id)
    await db.commit()
