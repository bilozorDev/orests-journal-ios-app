import logging
from datetime import datetime, timezone as dt_timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status, File, UploadFile
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.core.security import get_current_user_id
from app.core.authorization import verify_family_access, verify_pet_access, verify_medication_access
from app.models.pet import Pet
from app.models.medication import PetMedication, PetMedicationDose, PetMedicationPhoto
from app.models.notification import MedicationSchedule
from app.schemas.medication import (
    MedicationCreate, MedicationUpdate, MedicationResponse, MedicationListResponse,
    MedicationListItemResponse, MedicationWithSchedulesResponse, ScheduledTimeResponse,
    MedicationDeleteResponse, MedicationPhotoResponse,
)
from app.cache.helpers import cache_get, cache_set, cache_delete_pattern
from app.cache.keys import key_medications, TTL_ACTIVE_MEDS
from app.services.storage import storage_service
from app.services.apns import apns_service
from app.services.family_notifications import get_filtered_family_member_tokens

logger = logging.getLogger(__name__)

router = APIRouter()


async def invalidate_medication_caches(pet_id: UUID, family_id: str = None) -> None:
    """Invalidate dashboard and medication caches when medications change."""
    await cache_delete_pattern(f"dashboard:{pet_id}:*")
    if family_id:
        await cache_delete_pattern(f"medications:{family_id}:*")


async def notify_family_medication_change(
    db: AsyncSession,
    family_id: UUID,
    exclude_user_id: UUID,
    pet_name: str,
    medication_name: str,
    notification_type: str,
) -> None:
    """Send push notification to family members about medication changes.

    Args:
        db: Database session
        family_id: The family ID
        exclude_user_id: User ID to exclude (the user who made the change)
        pet_name: Name of the pet
        medication_name: Name of the medication
        notification_type: One of 'medication_created', 'medication_updated', 'medication_archived'
    """
    try:
        tokens = await get_filtered_family_member_tokens(
            db, family_id, exclude_user_id, notification_type
        )
        if not tokens:
            return

        # Build notification message
        if notification_type == "medication_created":
            title = f"New Medication: {pet_name}"
            body = f"{medication_name} was added"
        elif notification_type == "medication_updated":
            title = f"Medication Updated: {pet_name}"
            body = f"{medication_name} was updated"
        elif notification_type == "medication_archived":
            title = f"Medication Removed: {pet_name}"
            body = f"{medication_name} was archived"
        else:
            return

        await apns_service.send_to_multiple(
            device_tokens=tokens,
            title=title,
            body=body,
            data={
                "type": notification_type,
                "pet_name": pet_name,
                "medication_name": medication_name,
            },
        )
        logger.info(f"Sent {notification_type} notification to {len(tokens)} devices")
    except Exception as e:
        # Log but don't fail the main operation
        logger.error(f"Failed to send medication notification: {e}")


def validate_medication_input(med_in: MedicationCreate | MedicationUpdate, is_create: bool = True) -> None:
    """Validate medication input fields.

    Raises HTTPException for validation errors.
    """
    # Validate interval_days (1-30 for scheduled, None for PRN)
    if hasattr(med_in, 'interval_days') and med_in.interval_days is not None:
        if med_in.interval_days < 1 or med_in.interval_days > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="interval_days must be between 1 and 30"
            )

    # Validate times_per_day (1-8)
    if hasattr(med_in, 'times_per_day') and med_in.times_per_day is not None:
        if med_in.times_per_day < 1 or med_in.times_per_day > 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="times_per_day must be between 1 and 8"
            )

    # Validate end_date >= start_date
    if is_create:
        if hasattr(med_in, 'end_date') and med_in.end_date is not None:
            if hasattr(med_in, 'start_date') and med_in.start_date is not None:
                if med_in.end_date < med_in.start_date:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="end_date must be on or after start_date"
                    )

    # Validate as-needed medications don't have reminders or interval
    if hasattr(med_in, 'is_as_needed') and med_in.is_as_needed:
        if hasattr(med_in, 'reminders_enabled') and med_in.reminders_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="As-needed (PRN) medications cannot have reminders enabled"
            )


@router.get("", response_model=MedicationListResponse)
async def list_medications(
    family_id: str,
    response: Response,
    pet_id: Optional[UUID] = None,
    active_only: bool = False,
    include_archived: bool = False,
    timezone: str = "UTC",
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List medications for the family, optionally filtered by pet.

    Args:
        timezone: IANA timezone identifier (e.g., "America/Los_Angeles")
                  Used to determine "today" for active medication filtering.
        include_archived: If True, include archived medications in the response.
                         Default is False (archived medications are excluded).
        limit: Maximum number of medications to return (default 100, max 500).
        offset: Number of medications to skip (for pagination).
    """
    # Set cache control header for client-side caching
    response.headers["Cache-Control"] = "private, max-age=60, stale-while-revalidate=300"

    # Verify user belongs to this family
    await verify_family_access(db, user_id, family_id)

    # Try cache first (only for non-active queries which don't depend on timezone)
    if not active_only:
        cache_key = key_medications(
            family_id,
            str(pet_id) if pet_id else None,
            active_only,
            include_archived,
            offset,
            limit,
        )
        cached = await cache_get(cache_key, MedicationListResponse)
        if cached:
            return cached

    # First get pets for this family
    pets_query = select(Pet.id).where(Pet.family_id == family_id)
    pets_result = await db.execute(pets_query)
    pet_ids = [p for p in pets_result.scalars().all()]

    if not pet_ids:
        return MedicationListResponse(medications=[], total=0)

    # Build base filter conditions
    base_conditions = [PetMedication.pet_id.in_(pet_ids)]

    # Filter out archived medications unless explicitly requested
    if not include_archived:
        base_conditions.append(PetMedication.is_archived == False)

    if pet_id:
        base_conditions.append(PetMedication.pet_id == pet_id)

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

        base_conditions.append(PetMedication.start_date <= today_date)
        base_conditions.append(
            or_(
                PetMedication.end_date.is_(None),
                PetMedication.end_date >= today_date,
            )
        )

    # Get total count for pagination
    count_query = select(func.count()).select_from(PetMedication).where(and_(*base_conditions))
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Build medication query with pagination
    query = select(PetMedication).where(and_(*base_conditions))

    # Eager load schedules to avoid N+1 queries
    query = query.options(selectinload(PetMedication.schedules))
    query = query.order_by(PetMedication.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    medications = result.scalars().all()

    # Build response with scheduled times from eager-loaded relationship
    response_items = []
    for m in medications:
        item = MedicationListItemResponse.model_validate(m)
        item.scheduled_times = [
            ScheduledTimeResponse.model_validate(s) for s in m.schedules
        ]
        response_items.append(item)

    response_data = MedicationListResponse(medications=response_items, total=total)

    # Cache the response (only for non-active queries)
    if not active_only:
        cache_key = key_medications(
            family_id,
            str(pet_id) if pet_id else None,
            active_only,
            include_archived,
            offset,
            limit,
        )
        await cache_set(cache_key, response_data, TTL_ACTIVE_MEDS)

    return response_data


@router.post("", response_model=MedicationWithSchedulesResponse, status_code=status.HTTP_201_CREATED)
async def create_medication(
    med_in: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Create a new medication prescription."""
    # Validate input
    validate_medication_input(med_in, is_create=True)

    # Verify user has access to this pet through family membership
    pet = await verify_pet_access(db, user_id, med_in.pet_id)

    # Strip timezone info from dates (database uses naive UTC)
    start_date = med_in.start_date.replace(tzinfo=None) if med_in.start_date.tzinfo else med_in.start_date
    end_date = med_in.end_date.replace(tzinfo=None) if med_in.end_date and med_in.end_date.tzinfo else med_in.end_date

    # Set interval_days default for scheduled medications
    interval_days = med_in.interval_days
    if not med_in.is_as_needed and interval_days is None:
        interval_days = 1  # Default to daily for scheduled medications

    medication = PetMedication(
        pet_id=med_in.pet_id,
        name=med_in.name,
        friendly_name=med_in.friendly_name,
        medication_type=med_in.medication_type,
        dosage=med_in.dosage,
        interval_days=interval_days if not med_in.is_as_needed else None,
        is_as_needed=med_in.is_as_needed,
        start_date=start_date,
        end_date=end_date if not med_in.is_as_needed else None,  # PRN meds don't have end date
        times_per_day=med_in.times_per_day if not med_in.is_as_needed else 1,
        notes=med_in.notes,
        reminders_enabled=med_in.reminders_enabled if not med_in.is_as_needed else False,
        timezone=med_in.timezone,
        created_by=UUID(user_id),
    )
    db.add(medication)
    await db.commit()
    await db.refresh(medication)

    # Create scheduled times if provided (only for scheduled medications with reminders)
    scheduled_times = []
    if med_in.scheduled_times and not med_in.is_as_needed and med_in.reminders_enabled:
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
    await invalidate_medication_caches(med_in.pet_id, str(pet.family_id))

    # Send notification to family members - use friendly_name if set
    display_name = medication.friendly_name or medication.name
    await notify_family_medication_change(
        db=db,
        family_id=pet.family_id,
        exclude_user_id=UUID(user_id),
        pet_name=pet.name,
        medication_name=display_name,
        notification_type="medication_created",
    )

    # Re-fetch with photos loaded to avoid lazy loading issues
    med_query = (
        select(PetMedication)
        .options(selectinload(PetMedication.photos))
        .where(PetMedication.id == medication.id)
    )
    med_result = await db.execute(med_query)
    medication = med_result.scalar_one()

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

    # Fetch medication with photos
    med_query = (
        select(PetMedication)
        .options(selectinload(PetMedication.photos))
        .where(PetMedication.id == medication_id)
    )
    med_result = await db.execute(med_query)
    medication = med_result.scalar_one()

    # Fetch scheduled times
    schedules_result = await db.execute(
        select(MedicationSchedule).where(MedicationSchedule.medication_id == medication_id)
    )
    scheduled_times = list(schedules_result.scalars().all())

    response = MedicationWithSchedulesResponse.model_validate(medication)
    response.scheduled_times = [ScheduledTimeResponse.model_validate(s) for s in scheduled_times]
    response.photos = [MedicationPhotoResponse.model_validate(p) for p in medication.photos]
    return response


@router.patch("/{medication_id}", response_model=MedicationWithSchedulesResponse)
async def update_medication(
    medication_id: UUID,
    med_in: MedicationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a medication."""
    # Validate input
    validate_medication_input(med_in, is_create=False)

    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

    # Get pet for cache invalidation and notifications
    pet_result = await db.execute(select(Pet).where(Pet.id == medication.pet_id))
    pet = pet_result.scalar_one()
    family_id = str(pet.family_id)

    update_data = med_in.model_dump(exclude_unset=True)

    # Handle scheduled_times separately
    scheduled_times_data = update_data.pop('scheduled_times', None)

    # If switching to as-needed, clear reminders and related fields
    if update_data.get('is_as_needed') is True:
        update_data['reminders_enabled'] = False
        update_data['interval_days'] = None
        update_data['end_date'] = None
        # Clear scheduled times
        scheduled_times_data = []

    # Strip timezone info from dates (database uses naive UTC)
    if 'start_date' in update_data and update_data['start_date'] is not None:
        start_date = update_data['start_date']
        if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
            update_data['start_date'] = start_date.replace(tzinfo=None)

    if 'end_date' in update_data and update_data['end_date'] is not None:
        end_date = update_data['end_date']
        if hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
            update_data['end_date'] = end_date.replace(tzinfo=None)

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

        # Flush deletes before inserting new schedules to avoid unique constraint violation
        await db.flush()

        # Create new schedules (only if not as-needed and reminders enabled)
        if not medication.is_as_needed and medication.reminders_enabled:
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
    await invalidate_medication_caches(medication.pet_id, family_id)

    # Send notification to family members - use friendly_name if set
    display_name = medication.friendly_name or medication.name
    await notify_family_medication_change(
        db=db,
        family_id=pet.family_id,
        exclude_user_id=UUID(user_id),
        pet_name=pet.name,
        medication_name=display_name,
        notification_type="medication_updated",
    )

    # Re-fetch with photos loaded to avoid lazy loading issues
    med_query = (
        select(PetMedication)
        .options(selectinload(PetMedication.photos))
        .where(PetMedication.id == medication_id)
    )
    med_result = await db.execute(med_query)
    medication = med_result.scalar_one()

    response = MedicationWithSchedulesResponse.model_validate(medication)
    response.scheduled_times = [ScheduledTimeResponse.model_validate(s) for s in scheduled_times]
    return response


@router.delete("/{medication_id}", response_model=MedicationDeleteResponse)
async def delete_medication(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete or archive a medication based on dose history.

    If the medication has recorded doses, it will be archived to preserve history.
    If no doses exist, the medication will be hard deleted.
    """
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)
    pet_id = medication.pet_id
    medication_name = medication.friendly_name or medication.name  # Use friendly name for notifications

    # Get pet for cache invalidation and notifications
    pet_result = await db.execute(select(Pet).where(Pet.id == pet_id))
    pet = pet_result.scalar_one()
    family_id = str(pet.family_id)

    # Check if medication has any doses
    dose_count_query = select(func.count()).select_from(PetMedicationDose).where(
        PetMedicationDose.medication_id == medication_id
    )
    dose_count_result = await db.execute(dose_count_query)
    dose_count = dose_count_result.scalar() or 0

    # Get photo URLs for cleanup if hard deleting
    photo_urls = []
    if dose_count == 0:
        photos_query = select(PetMedicationPhoto).where(PetMedicationPhoto.medication_id == medication_id)
        photos_result = await db.execute(photos_query)
        photos = photos_result.scalars().all()
        photo_urls = [photo.photo_url for photo in photos]

    if dose_count > 0:
        # Archive instead of delete to preserve history
        medication.is_archived = True
        await db.commit()
        await invalidate_medication_caches(pet_id, family_id)

        # Send notification
        await notify_family_medication_change(
            db=db,
            family_id=pet.family_id,
            exclude_user_id=UUID(user_id),
            pet_name=pet.name,
            medication_name=medication_name,
            notification_type="medication_archived",
        )

        return MedicationDeleteResponse(
            deleted=False,
            archived=True,
            message=f"Medication has {dose_count} dose record(s). It has been archived instead of deleted to preserve history."
        )
    else:
        # Hard delete since no doses exist
        await db.delete(medication)
        await db.commit()
        await invalidate_medication_caches(pet_id, family_id)

        # Delete photos from R2 AFTER DB commit succeeds
        for photo_url in photo_urls:
            try:
                deleted = await storage_service.delete_image(photo_url)
                if deleted:
                    logger.info(f"Deleted medication photo on delete: {photo_url}")
            except Exception as e:
                logger.error(f"Failed to delete medication photo: {e}")

        # Send notification
        await notify_family_medication_change(
            db=db,
            family_id=pet.family_id,
            exclude_user_id=UUID(user_id),
            pet_name=pet.name,
            medication_name=medication_name,
            notification_type="medication_archived",
        )

        return MedicationDeleteResponse(
            deleted=True,
            archived=False,
            message="Medication deleted successfully."
        )


@router.post("/{medication_id}/unarchive", response_model=MedicationResponse)
async def unarchive_medication(
    medication_id: UUID,
    family_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Restore an archived medication.

    Args:
        medication_id: UUID of the medication to unarchive
        family_id: The family ID (required for authorization)
    """
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

    if not medication.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Medication is not archived"
        )

    # Get pet for cache invalidation and notifications
    pet_result = await db.execute(select(Pet).where(Pet.id == medication.pet_id))
    pet = pet_result.scalar_one()

    # Unarchive the medication
    medication.is_archived = False
    await db.commit()

    # Invalidate caches
    await invalidate_medication_caches(medication.pet_id, str(pet.family_id))

    # Load scheduled times for response
    await db.refresh(medication, ["scheduled_times", "photos"])

    # Build response with scheduled times
    scheduled_times = [
        ScheduledTimeResponse(
            id=st.id,
            scheduled_hour=st.scheduled_hour,
            scheduled_minute=st.scheduled_minute
        )
        for st in (medication.scheduled_times or [])
    ]

    # Build photos list
    photos = [
        MedicationPhotoResponse(
            id=photo.id,
            medication_id=photo.medication_id,
            photo_url=photo.photo_url,
            created_at=photo.created_at
        )
        for photo in (medication.photos or [])
    ]

    # Send notification to family members
    await notify_family_medication_change(
        db=db,
        family_id=pet.family_id,
        exclude_user_id=UUID(user_id),
        pet_name=pet.name,
        medication_name=medication.friendly_name or medication.name,
        notification_type="medication_updated",
    )

    return MedicationResponse(
        id=medication.id,
        pet_id=medication.pet_id,
        name=medication.name,
        friendly_name=medication.friendly_name,
        medication_type=medication.medication_type,
        dosage=medication.dosage,
        interval_days=medication.interval_days,
        is_as_needed=medication.is_as_needed,
        start_date=medication.start_date,
        end_date=medication.end_date,
        times_per_day=medication.times_per_day,
        notes=medication.notes,
        reminders_enabled=medication.reminders_enabled,
        timezone=medication.timezone,
        is_archived=medication.is_archived,
        created_by=medication.created_by,
        created_at=medication.created_at,
        scheduled_times=scheduled_times,
        photos=photos,
    )


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
                PetMedication.is_archived == False,  # Exclude archived medications
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


# ============== Photo Endpoints ==============

@router.post("/{medication_id}/photos", response_model=MedicationPhotoResponse)
async def upload_medication_photo(
    medication_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Upload a photo for a medication (appends to existing photos)."""
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

    # Check photo limit (max 3 photos per medication)
    photo_count_query = select(func.count(PetMedicationPhoto.id)).where(
        PetMedicationPhoto.medication_id == medication_id
    )
    photo_count_result = await db.execute(photo_count_query)
    current_count = photo_count_result.scalar() or 0

    if current_count >= 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 3 photos per medication"
        )

    # Get pet for family_id
    pet_query = select(Pet).where(Pet.id == medication.pet_id)
    pet_result = await db.execute(pet_query)
    pet = pet_result.scalar_one()

    # Upload photo to R2
    photo_url = await storage_service.upload_image(
        file=file,
        upload_type="medication-photo",
        family_id=str(pet.family_id),
    )

    # Create photo record
    photo = PetMedicationPhoto(
        medication_id=medication_id,
        photo_url=photo_url,
        sort_order=current_count,  # Append at end
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    # Invalidate cache
    await invalidate_medication_caches(medication.pet_id, str(pet.family_id))

    return MedicationPhotoResponse.model_validate(photo)


@router.delete("/{medication_id}/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication_photo(
    medication_id: UUID,
    photo_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a specific photo from a medication."""
    # Verify user has access to this medication through family membership
    medication = await verify_medication_access(db, user_id, medication_id)

    # Get the photo
    photo_query = select(PetMedicationPhoto).where(
        PetMedicationPhoto.id == photo_id,
        PetMedicationPhoto.medication_id == medication_id,
    )
    photo_result = await db.execute(photo_query)
    photo = photo_result.scalar_one_or_none()

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found"
        )

    # Store URL before deleting record
    photo_url = photo.photo_url

    # Delete photo record from DB first
    await db.delete(photo)
    await db.commit()

    # Delete photo from R2 AFTER DB commit succeeds
    try:
        deleted = await storage_service.delete_image(photo_url)
        if deleted:
            logger.info(f"Deleted medication photo: {photo_url}")
    except Exception as e:
        logger.error(f"Failed to delete medication photo from R2: {e}")

    # Invalidate cache
    pet_query = select(Pet).where(Pet.id == medication.pet_id)
    pet_result = await db.execute(pet_query)
    pet = pet_result.scalar_one()
    await invalidate_medication_caches(medication.pet_id, str(pet.family_id))
