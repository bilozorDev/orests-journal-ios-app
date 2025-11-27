from datetime import datetime, timezone as dt_timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.core.authorization import verify_family_access, verify_pet_access, verify_medication_access
from app.models.pet import Pet
from app.models.medication import PetMedication
from app.models.notification import MedicationSchedule
from app.schemas.medication import (
    MedicationCreate, MedicationUpdate, MedicationResponse, MedicationListResponse,
    MedicationWithSchedulesResponse, ScheduledTimeResponse,
)
from app.cache.helpers import cache_get, cache_set, cache_delete_pattern
from app.cache.keys import key_medications, TTL_ACTIVE_MEDS

router = APIRouter()


async def invalidate_medication_caches(pet_id: UUID, org_id: str = None) -> None:
    """Invalidate dashboard and medication caches when medications change."""
    await cache_delete_pattern(f"dashboard:{pet_id}:*")
    if org_id:
        await cache_delete_pattern(f"medications:{org_id}:*")


@router.get("", response_model=MedicationListResponse)
async def list_medications(
    org_id: str,
    response: Response,
    pet_id: Optional[UUID] = None,
    active_only: bool = False,
    timezone: str = "UTC",
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List medications for the organization, optionally filtered by pet.

    Args:
        timezone: IANA timezone identifier (e.g., "America/Los_Angeles")
                  Used to determine "today" for active medication filtering.
    """
    # Set cache control header for client-side caching
    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=300"

    # Verify user belongs to this family
    await verify_family_access(db, user_id, org_id)

    # Try cache first (only for non-active queries which don't depend on timezone)
    if not active_only:
        cache_key = key_medications(org_id, str(pet_id) if pet_id else None, active_only)
        cached = await cache_get(cache_key, MedicationListResponse)
        if cached:
            return cached

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
        # Parse timezone, fallback to UTC if invalid
        try:
            tz = ZoneInfo(timezone)
        except Exception:
            tz = ZoneInfo("UTC")

        # Get current date in user's local timezone
        now_utc = datetime.now(dt_timezone.utc)
        now_local = now_utc.astimezone(tz)
        today_date = now_local.date()

        query = query.where(
            and_(
                PetMedication.start_date <= today_date,
                or_(
                    PetMedication.end_date.is_(None),
                    PetMedication.end_date >= today_date,
                ),
            )
        )

    query = query.order_by(PetMedication.created_at.desc())
    result = await db.execute(query)
    medications = result.scalars().all()

    response = MedicationListResponse(
        medications=[MedicationResponse.model_validate(m) for m in medications]
    )

    # Cache the response (only for non-active queries)
    if not active_only:
        cache_key = key_medications(org_id, str(pet_id) if pet_id else None, active_only)
        await cache_set(cache_key, response, TTL_ACTIVE_MEDS)

    return response


@router.post("", response_model=MedicationWithSchedulesResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
    med_in: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new medication prescription."""
    # Verify user has access to this pet through family membership
    pet = await verify_pet_access(db, user_id, med_in.pet_id)

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
        reminders_enabled=med_in.reminders_enabled,
        timezone=med_in.timezone,
        created_by=UUID(user_id),
    )
    db.add(medication)
    await db.commit()
    await db.refresh(medication)

    # Create scheduled times if provided
    scheduled_times = []
    if med_in.scheduled_times:
        for schedule in med_in.scheduled_times:
            sched = MedicationSchedule(
                medication_id=medication.id,
                scheduled_hour=schedule.hour,
                scheduled_minute=schedule.minute,
            )
            db.add(sched)
            scheduled_times.append(sched)
        await db.commit()
        for sched in scheduled_times:
            await db.refresh(sched)

    # Invalidate caches
    await invalidate_medication_caches(med_in.pet_id, str(pet.org_id))

    response = MedicationWithSchedulesResponse.model_validate(medication)
    response.scheduled_times = [ScheduledTimeResponse.model_validate(s) for s in scheduled_times]
    return response


@router.get("/{medication_id}", response_model=MedicationWithSchedulesResponse)
async def get_medication(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a specific medication by ID."""
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

    # Fetch scheduled times
    schedules_result = await db.execute(
        select(MedicationSchedule).where(MedicationSchedule.medication_id == medication_id)
    )
    scheduled_times = list(schedules_result.scalars().all())

    response = MedicationWithSchedulesResponse.model_validate(medication)
    response.scheduled_times = [ScheduledTimeResponse.model_validate(s) for s in scheduled_times]
    return response


@router.patch("/{medication_id}", response_model=MedicationWithSchedulesResponse)
async def update_medication(
    medication_id: UUID,
    med_in: MedicationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a medication."""
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

    # Get org_id from pet for cache invalidation
    pet_result = await db.execute(select(Pet.org_id).where(Pet.id == medication.pet_id))
    org_id = str(pet_result.scalar_one())

    update_data = med_in.model_dump(exclude_unset=True)

    # Handle scheduled_times separately
    scheduled_times_data = update_data.pop('scheduled_times', None)

    for field, value in update_data.items():
        setattr(medication, field, value)

    await db.commit()
    await db.refresh(medication)

    # Update scheduled times if provided
    scheduled_times = []
    if scheduled_times_data is not None:
        # Delete existing schedules
        existing = await db.execute(
            select(MedicationSchedule).where(MedicationSchedule.medication_id == medication_id)
        )
        for sched in existing.scalars().all():
            await db.delete(sched)

        # Create new schedules
        for schedule in scheduled_times_data:
            sched = MedicationSchedule(
                medication_id=medication_id,
                scheduled_hour=schedule['hour'],
                scheduled_minute=schedule.get('minute', 0),
            )
            db.add(sched)
            scheduled_times.append(sched)
        await db.commit()
        for sched in scheduled_times:
            await db.refresh(sched)
    else:
        # Fetch existing schedules
        existing = await db.execute(
            select(MedicationSchedule).where(MedicationSchedule.medication_id == medication_id)
        )
        scheduled_times = list(existing.scalars().all())

    # Invalidate caches
    await invalidate_medication_caches(medication.pet_id, org_id)

    response = MedicationWithSchedulesResponse.model_validate(medication)
    response.scheduled_times = [ScheduledTimeResponse.model_validate(s) for s in scheduled_times]
    return response


@router.delete("/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a medication."""
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)
    pet_id = medication.pet_id

    # Get org_id from pet for cache invalidation
    pet_result = await db.execute(select(Pet.org_id).where(Pet.id == pet_id))
    org_id = str(pet_result.scalar_one())

    await db.delete(medication)
    await db.commit()

    # Invalidate caches
    await invalidate_medication_caches(pet_id, org_id)


@router.get("/pet/{pet_id}/active", response_model=MedicationListResponse)
async def get_active_medications_for_pet(
    pet_id: UUID,
    timezone: str = "UTC",
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get active medications for a specific pet.

    Args:
        timezone: IANA timezone identifier (e.g., "America/Los_Angeles")
                  Used to determine "today" for active medication filtering.
    """
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    # Parse timezone, fallback to UTC if invalid
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        tz = ZoneInfo("UTC")

    # Get current date in user's local timezone
    now_utc = datetime.now(dt_timezone.utc)
    now_local = now_utc.astimezone(tz)
    today_date = now_local.date()

    query = (
        select(PetMedication)
        .where(
            and_(
                PetMedication.pet_id == pet_id,
                PetMedication.start_date <= today_date,
                or_(
                    PetMedication.end_date.is_(None),
                    PetMedication.end_date >= today_date,
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
