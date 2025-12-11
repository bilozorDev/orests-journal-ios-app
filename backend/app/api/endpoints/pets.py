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

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=PetListResponse)
async def list_pets(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    org_id: Optional[str] = None,
):
    """List all pets for the user's family."""
    # org_id is the family ID
    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="org_id query parameter is required",
        )

    # Verify user belongs to this family
    await verify_family_access(db, user_id, org_id)

    query = select(Pet).where(Pet.org_id == org_id).order_by(Pet.created_at.desc())
    result = await db.execute(query)
    pets = result.scalars().all()

    return PetListResponse(pets=[PetResponse.model_validate(p) for p in pets])


@router.post("", response_model=PetResponse, status_code=status.HTTP_201_CREATED)
async def create_pet(
    pet_in: PetCreate,
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new pet for the organization (family)."""
    # Verify user belongs to this family
    await verify_family_access(db, user_id, org_id)

    pet = Pet(
        org_id=UUID(org_id),
        name=pet_in.name,
        kind=pet_in.kind,
        photo_url=pet_in.photo_url,
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
        # Treat empty string as None for photo_url (iOS sends "" to clear photo)
        if field == "photo_url" and value == "":
            value = None
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

    # Store photo URL for cleanup before deleting
    photo_url = pet.photo_url

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
