from datetime import datetime, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import ClerkUser, get_current_user
from app.models.medication import PetMedication, PetMedicationDose
from app.schemas.medication import DoseCreate, DoseResponse, DoseListResponse

router = APIRouter()


@router.post("", response_model=DoseResponse, status_code=status.HTTP_201_CREATED)
async def record_dose(
    dose_in: DoseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Record a medication dose."""
    # Verify medication exists
    med_query = select(PetMedication).where(PetMedication.id == dose_in.medication_id)
    result = await db.execute(med_query)
    medication = result.scalar_one_or_none()

    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication not found",
        )

    dose = PetMedicationDose(
        medication_id=dose_in.medication_id,
        given_at=dose_in.given_at or datetime.utcnow(),
        given_by=current_user.id,
        notes=dose_in.notes,
    )
    db.add(dose)
    await db.commit()
    await db.refresh(dose)

    return DoseResponse.model_validate(dose)


@router.get("/medication/{medication_id}", response_model=DoseListResponse)
async def list_doses(
    medication_id: UUID,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """List doses for a medication."""
    query = (
        select(PetMedicationDose)
        .where(PetMedicationDose.medication_id == medication_id)
        .order_by(PetMedicationDose.given_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    doses = result.scalars().all()

    return DoseListResponse(doses=[DoseResponse.model_validate(d) for d in doses])


@router.get("/medication/{medication_id}/today", response_model=DoseListResponse)
async def get_today_doses(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Get today's doses for a medication."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    query = (
        select(PetMedicationDose)
        .where(
            and_(
                PetMedicationDose.medication_id == medication_id,
                PetMedicationDose.given_at >= today,
                PetMedicationDose.given_at < tomorrow,
            )
        )
        .order_by(PetMedicationDose.given_at.desc())
    )
    result = await db.execute(query)
    doses = result.scalars().all()

    return DoseListResponse(doses=[DoseResponse.model_validate(d) for d in doses])


@router.get("/medication/{medication_id}/last", response_model=DoseResponse)
async def get_last_dose(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Get the most recent dose for a medication."""
    query = (
        select(PetMedicationDose)
        .where(PetMedicationDose.medication_id == medication_id)
        .order_by(PetMedicationDose.given_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    dose = result.scalar_one_or_none()

    if not dose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No doses recorded",
        )

    return DoseResponse.model_validate(dose)


@router.delete("/{dose_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dose(
    dose_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: ClerkUser = Depends(get_current_user),
):
    """Delete a dose record."""
    query = select(PetMedicationDose).where(PetMedicationDose.id == dose_id)
    result = await db.execute(query)
    dose = result.scalar_one_or_none()

    if not dose:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dose not found",
        )

    await db.delete(dose)
    await db.commit()
