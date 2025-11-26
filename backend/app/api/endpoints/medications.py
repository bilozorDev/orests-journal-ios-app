from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.core.authorization import verify_family_access, verify_pet_access, verify_medication_access
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
    user_id: str = Depends(get_current_user_id),
):
    """List medications for the organization, optionally filtered by pet."""
    # Verify user belongs to this family
    await verify_family_access(db, user_id, org_id)

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
    user_id: str = Depends(get_current_user_id),
):
    """Create a new medication prescription."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, med_in.pet_id)

    # Strip timezone info from dates (database uses naive UTC)
    start_date = med_in.start_date.replace(tzinfo=None) if med_in.start_date.tzinfo else med_in.start_date
    end_date = med_in.end_date.replace(tzinfo=None) if med_in.end_date and med_in.end_date.tzinfo else med_in.end_date

    medication = PetMedication(
        pet_id=med_in.pet_id,
        name=med_in.name,
        medication_type=med_in.medication_type,
        start_date=start_date,
        end_date=end_date,
        times_per_day=med_in.times_per_day,
        notes=med_in.notes,
        created_by=user_id,
    )
    db.add(medication)
    await db.commit()
    await db.refresh(medication)

    return MedicationResponse.model_validate(medication)


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific medication by ID."""
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

    return MedicationResponse.model_validate(medication)


@router.patch("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: UUID,
    med_in: MedicationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a medication."""
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

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
    user_id: str = Depends(get_current_user_id),
):
    """Delete a medication."""
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

    await db.delete(medication)
    await db.commit()


@router.get("/pet/{pet_id}/active", response_model=MedicationListResponse)
async def get_active_medications_for_pet(
    pet_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get active medications for a specific pet."""
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

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
