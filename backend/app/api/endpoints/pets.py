import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.core.authorization import verify_family_access, verify_pet_access
from app.models.pet import Pet, HealthRecord
from app.schemas.pet import (
    PetCreate, PetUpdate, PetResponse, PetListResponse,
    HealthRecordCreate, HealthRecordResponse,
)
from app.services.storage import storage_service
from app.services.apns import apns_service
from app.services.family_notifications import get_filtered_family_member_tokens
from app.cache.helpers import cache_get, cache_set, cache_delete
from app.cache.keys import key_pets, TTL_PETS

logger = logging.getLogger(__name__)

router = APIRouter()


def validate_photo_url(photo_url: Optional[str], family_id: str) -> Optional[str]:
    """Validate that a photo URL belongs to the expected R2 storage and family.

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

    # Extract and validate path: folder/family_id/filename
    path = photo_url.replace(f"{public_url_base}/", "")
    path_parts = path.split("/")

    if len(path_parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid photo URL format"
        )

    folder, url_family_id, filename = path_parts

    # Validate family_id matches (security check)
    if url_family_id != family_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Photo URL belongs to a different family"
        )

    return photo_url


async def notify_family_pet_change(
    db: AsyncSession,
    family_id: UUID,
    exclude_user_id: UUID,
    notification_type: str,
    pet_name: str,
    pet_id: UUID,
) -> None:
    """Send push notification to other family members about pet changes.

    Args:
        db: Database session
        family_id: The family ID
        exclude_user_id: User who triggered the change (won't receive notification)
        notification_type: One of 'pet_added', 'pet_updated', 'pet_deleted'
        pet_name: Name of the pet for notification text
        pet_id: ID of the pet
    """
    tokens = await get_filtered_family_member_tokens(db, family_id, exclude_user_id, notification_type)
    if not tokens:
        return

    titles = {
        "pet_added": f"{pet_name} was added",
        "pet_updated": f"{pet_name} was updated",
        "pet_deleted": f"{pet_name} was removed",
    }

    await apns_service.send_to_multiple(
        device_tokens=tokens,
        title=titles.get(notification_type, "Pet updated"),
        body="Tap to refresh",
        data={
            "type": notification_type,
            "family_id": str(family_id),
            "pet_id": str(pet_id),
            "pet_name": pet_name,
        },
    )


@router.get("", response_model=PetListResponse)
async def list_pets(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    family_id: Optional[str] = None,
):
    """List all pets for the user's family."""
    if not family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="family_id query parameter is required",
        )

    # Verify user belongs to this family
    await verify_family_access(db, user_id, family_id)

    # Check cache first
    cache_key = key_pets(family_id)
    cached = await cache_get(cache_key, PetListResponse)
    if cached:
        return cached

    # Fetch from database
    query = select(Pet).where(Pet.family_id == family_id).order_by(Pet.created_at.desc())
    result = await db.execute(query)
    pets = result.scalars().all()

    response = PetListResponse(pets=[PetResponse.model_validate(p) for p in pets])

    # Cache the response
    await cache_set(cache_key, response, TTL_PETS)

    return response


@router.post("", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
async def create_pet(
    pet_in: PetCreate,
    family_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new pet for the family."""
    # Verify user belongs to this family
    await verify_family_access(db, user_id, family_id)

    # Validate photo URL belongs to this family
    validated_photo_url = validate_photo_url(pet_in.photo_url, family_id)

    pet = Pet(
        family_id=UUID(family_id),
        name=pet_in.name,
        kind=pet_in.kind,
        photo_url=validated_photo_url,
        current_weight=pet_in.current_weight,
        date_of_birth=pet_in.date_of_birth,
        created_by=UUID(user_id),
    )
    db.add(pet)
    await db.flush()

    # Create initial health record if weight provided
    if pet_in.current_weight:
        health_record = HealthRecord(
            pet_id=pet.id,
            weight_pounds=pet_in.current_weight,
            notes="Initial weight record",
        )
        db.add(health_record)

    await db.commit()
    await db.refresh(pet)

    # Invalidate cache and notify other family members
    await cache_delete(key_pets(family_id))
    await notify_family_pet_change(
        db, pet.family_id, UUID(user_id), "pet_added", pet.name, pet.id
    )

    return PetResponse.model_validate(pet)


@router.get("/{pet_id}", response_model=PetResponse)
async def get_pet(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific pet by ID."""
    # Verify user has access to this pet through family membership
    pet = await verify_pet_access(db, user_id, pet_id)

    return PetResponse.model_validate(pet)


@router.patch("/{pet_id}", response_model=PetResponse)
async def update_pet(
    pet_id: UUID,
    pet_in: PetUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a pet."""
    # Verify user has access to this pet through family membership
    pet = await verify_pet_access(db, user_id, pet_id)

    # Store old photo URL for cleanup
    old_photo_url = pet.photo_url

    # Update fields
    update_data = pet_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        # Validate and handle photo_url
        if field == "photo_url":
            # Validate photo URL belongs to this family (or is empty for removal)
            value = validate_photo_url(value, str(pet.family_id))
        setattr(pet, field, value)

    await db.commit()
    await db.refresh(pet)

    # Clean up old photo from R2 if it was replaced or cleared
    if old_photo_url and old_photo_url != pet.photo_url:
        try:
            deleted = await storage_service.delete_image(old_photo_url)
            if deleted:
                logger.info(f"Deleted old pet photo: {old_photo_url}")
        except Exception as e:
            # Don't fail the update if photo cleanup fails
            logger.error(f"Failed to delete old pet photo: {e}")

    # Invalidate cache and notify other family members
    await cache_delete(key_pets(str(pet.family_id)))
    await notify_family_pet_change(
        db, pet.family_id, UUID(user_id), "pet_updated", pet.name, pet.id
    )

    return PetResponse.model_validate(pet)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a pet."""
    # Verify user has access to this pet through family membership
    pet = await verify_pet_access(db, user_id, pet_id)

    # Store data for cleanup and notification before deleting
    photo_url = pet.photo_url
    family_id = pet.family_id
    pet_name = pet.name

    await db.delete(pet)
    await db.commit()

    # Clean up photo from R2 after successful deletion
    if photo_url:
        try:
            deleted = await storage_service.delete_image(photo_url)
            if deleted:
                logger.info(f"Deleted pet photo on pet deletion: {photo_url}")
        except Exception as e:
            # Don't fail the delete if photo cleanup fails
            logger.error(f"Failed to delete pet photo on pet deletion: {e}")

    # Invalidate cache and notify other family members
    await cache_delete(key_pets(str(family_id)))
    await notify_family_pet_change(
        db, family_id, UUID(user_id), "pet_deleted", pet_name, pet_id
    )


# Health Records
@router.post("/{pet_id}/health-records", response_model=HealthRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_health_record(
    pet_id: UUID,
    record_in: HealthRecordCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a health record for a pet."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    record = HealthRecord(
        pet_id=pet_id,
        age_years=record_in.age_years,
        weight_pounds=record_in.weight_pounds,
        notes=record_in.notes,
    )
    db.add(record)

    # Update pet's current_weight if weight was recorded
    if record_in.weight_pounds is not None:
        pet = await db.get(Pet, pet_id)
        if pet:
            pet.current_weight = record_in.weight_pounds

    await db.commit()
    await db.refresh(record)

    # Invalidate pet cache since weight was updated
    if record_in.weight_pounds is not None and pet:
        await cache_delete(key_pets(str(pet.family_id)))

    return HealthRecordResponse.model_validate(record)


@router.get("/{pet_id}/health-records", response_model=list[HealthRecordResponse])
async def list_health_records(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List health records for a pet."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    query = (
        select(HealthRecord)
        .where(HealthRecord.pet_id == pet_id)
        .order_by(HealthRecord.recorded_at.desc())
    )
    result = await db.execute(query)
    records = result.scalars().all()

    return [HealthRecordResponse.model_validate(r) for r in records]
