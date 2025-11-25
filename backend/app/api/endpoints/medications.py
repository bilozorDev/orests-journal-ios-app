from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import ClerkUser, get_current_user
from app.models.pet import Pet
from app.models.medication import PetMedication
from app.schemas.medication import (
    MedicationCreate, MedicationUpdate, MedicationResponse, MedicationListResponse,
)

router = APIRouter()


@router.get("", response_model=MedicationListResponse)
async def list_medications(
    org_id: str,
    pet_id: Optional[UUID] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """List medications for the organization, optionally filtered by pet."""
    # First get pets for this org
    pets_query = select(Pet.id).where(Pet.org_id == org_id)
    pets_result = await db.execute(pets_query)
    pet_ids = [p for p in pets_result.scalars().all()]

    if not pet_ids:
        return MedicationListResponse(medications=[])

    # Build medication query
    query = select(PetMedication).where(PetMedication.pet_id.in_(pet_ids))

    if pet_id:
        query = query.where(PetMedication.pet_id == pet_id)

    if active_only:
        now = datetime.utcnow()
        query = query.where(
            and_(
                PetMedication.start_date <= now,
                or_(
                    PetMedication.end_date.is_(None),
                    PetMedication.end_date >= now,
                ),
            )
        )

    query = query.order_by(PetMedication.created_at.desc())
    result = await db.execute(query)
    medications = result.scalars().all()

    return MedicationListResponse(
        medications=[MedicationResponse.model_validate(m) for m in medications]
    )


@router.post("", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
    med_in: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Create a new medication prescription."""
    # Verify pet exists
    pet_query = select(Pet).where(Pet.id == med_in.pet_id)
    result = await db.execute(pet_query)
    pet = result.scalar_one_or_none()

    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )

    medication = PetMedication(
        pet_id=med_in.pet_id,
        name=med_in.name,
        medication_type=med_in.medication_type,
        start_date=med_in.start_date,
        end_date=med_in.end_date,
        times_per_day=med_in.times_per_day,
        notes=med_in.notes,
        created_by=current_user.id,
    )
    db.add(medication)
    await db.commit()
    await db.refresh(medication)

    return MedicationResponse.model_validate(medication)


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Get a specific medication by ID."""
    query = select(PetMedication).where(PetMedication.id == medication_id)
    result = await db.execute(query)
    medication = result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    return MedicationResponse.model_validate(medication)


@router.patch("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: UUID,
    med_in: MedicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Update a medication."""
    query = select(PetMedication).where(PetMedication.id == medication_id)
    result = await db.execute(query)
    medication = result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    update_data = med_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(medication, field, value)

    await db.commit()
    await db.refresh(medication)

    return MedicationResponse.model_validate(medication)


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Delete a medication."""
    query = select(PetMedication).where(PetMedication.id == medication_id)
    result = await db.execute(query)
    medication = result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    await db.delete(medication)
    await db.commit()


@router.get("/pet/{pet_id}/active", response_model=MedicationListResponse)
async def get_active_medications_for_pet(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Get active medications for a specific pet."""
    now = datetime.utcnow()

    query = (
        select(PetMedication)
        .where(
            and_(
                PetMedication.pet_id == pet_id,
                PetMedication.start_date <= now,
                or_(
                    PetMedication.end_date.is_(None),
                    PetMedication.end_date >= now,
                ),
            )
        )
        .order_by(PetMedication.created_at.desc())
    )
    result = await db.execute(query)
    medications = result.scalars().all()

    return MedicationListResponse(
        medications=[MedicationResponse.model_validate(m) for m in medications]
    )
