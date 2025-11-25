from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.models.pet import Pet, HealthRecord
from app.schemas.pet import (
    PetCreate, PetUpdate, PetResponse, PetListResponse,
    HealthRecordCreate, HealthRecordResponse,
)

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
    pet = Pet(
        org_id=org_id,
        name=pet_in.name,
        kind=pet_in.kind,
        photo_url=pet_in.photo_url,
        current_weight=pet_in.current_weight,
        created_by=user_id,
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
    query = select(Pet).where(Pet.id == pet_id)
    result = await db.execute(query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    return PetResponse.model_validate(pet)


@router.patch("/{pet_id}", response_model=PetResponse)
async def update_pet(
    pet_id: UUID,
    pet_in: PetUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a pet."""
    query = select(Pet).where(Pet.id == pet_id)
    result = await db.execute(query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    # Update fields
    update_data = pet_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pet, field, value)

    await db.commit()
    await db.refresh(pet)

    return PetResponse.model_validate(pet)


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pet(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a pet."""
    query = select(Pet).where(Pet.id == pet_id)
    result = await db.execute(query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    await db.delete(pet)
    await db.commit()


# Health Records
@router.post("/{pet_id}/health-records", response_model=HealthRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_health_record(
    pet_id: UUID,
    record_in: HealthRecordCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a health record for a pet."""
    # Verify pet exists
    pet_query = select(Pet).where(Pet.id == pet_id)
    result = await db.execute(pet_query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    record = HealthRecord(
        pet_id=pet_id,
        age_years=record_in.age_years,
        weight_pounds=record_in.weight_pounds,
        notes=record_in.notes,
    )
    db.add(record)
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
    query = (
        select(HealthRecord)
        .where(HealthRecord.pet_id == pet_id)
        .order_by(HealthRecord.recorded_at.desc())
    )
    result = await db.execute(query)
    records = result.scalars().all()

    return [HealthRecordResponse.model_validate(r) for r in records]
