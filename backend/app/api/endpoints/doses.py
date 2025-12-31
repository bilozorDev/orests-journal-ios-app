import logging
from datetime import UTC, datetime, timedelta, timezone as dt_timezone
from typing import Dict
from uuid import UUID
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.core.security import get_current_user_id
from app.core.authorization import verify_medication_access, verify_dose_access, verify_family_access, verify_pet_access
from app.core.utils import format_user_name
from app.models.medication import PetMedication, PetMedicationDose
from app.models.pet import Pet
from app.models.user import User
from app.schemas.medication import (
    DoseCreate, DoseUpdate, DoseResponse, DoseDetailResponse, DoseListResponse,
    AllDoseDetailResponse, AllDosesListResponse,
)
from app.cache.helpers import cache_delete_pattern, cache_get, cache_set, cache_delete
from app.cache.keys import key_today_doses, key_last_dose, TTL_DOSE_COUNTS, TTL_LAST_DOSE
from app.services.family_notifications import get_filtered_family_member_tokens
from app.services.apns import apns_service

logger = logging.getLogger(__name__)

router = APIRouter()


async def invalidate_dose_caches(db: AsyncSession, medication_id: UUID) -> None:
    """Invalidate dashboard and dose-specific caches when doses change."""
    # Get the pet_id from the medication
    result = await db.execute(
        select(PetMedication.pet_id).where(PetMedication.id == medication_id)
    )
    pet_id = result.scalar_one_or_none()
    if pet_id:
        await cache_delete_pattern(f"dashboard:{pet_id}:*")

    # Invalidate medication-specific dose caches
    med_id_str = str(medication_id)
    await cache_delete(key_last_dose(med_id_str))
    await cache_delete_pattern(f"today_doses:{med_id_str}:*")


async def notify_family_dose_administered(
    db: AsyncSession,
    family_id: UUID,
    exclude_user_id: UUID,
    user_name: str,
    pet_name: str,
    medication_name: str,
) -> None:
    """Send push notification to family members when a dose is administered.

    Args:
        db: Database session
        family_id: The family ID
        exclude_user_id: User ID to exclude (the user who gave the dose)
        user_name: Name of the user who gave the dose
        pet_name: Name of the pet
        medication_name: Name of the medication
    """
    try:
        tokens = await get_filtered_family_member_tokens(
            db, family_id, exclude_user_id, "dose_administered"
        )
        if not tokens:
            return

        title = f"Dose Recorded: {pet_name}"
        body = f"{user_name} gave {pet_name} {medication_name}"

        await apns_service.send_to_multiple(
            device_tokens=tokens,
            title=title,
            body=body,
            data={
                "type": "dose_administered",
                "pet_name": pet_name,
                "medication_name": medication_name,
            },
        )
        logger.info(f"Sent dose_administered notification to {len(tokens)} devices")
    except Exception as e:
        logger.error(f"Failed to send dose_administered notification: {e}")


@router.post("", response_model=DoseResponse, status_code=status.HTTP_201_CREATED)
async def record_dose(
    dose_in: DoseCreate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Record a medication dose."""
    # Verify user has access to this medication through family membership
    await verify_medication_access(db, user_id, dose_in.medication_id)

    # Get medication with pet info for notification
    med_query = (
        select(PetMedication, Pet)
        .join(Pet, PetMedication.pet_id == Pet.id)
        .where(PetMedication.id == dose_in.medication_id)
    )
    med_result = await db.execute(med_query)
    med_row = med_result.first()
    if not med_row:
        raise HTTPException(status_code=404, detail="Medication not found")
    medication = med_row[0]
    pet = med_row[1]

    # Check if medication is archived
    if medication.is_archived:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record doses for an archived medication. Unarchive it first."
        )

    # Get current user for notification
    user_result = await db.execute(select(User).where(User.id == UUID(user_id)))
    current_user = user_result.scalar_one()
    user_name = format_user_name(current_user.first_name, current_user.last_name)

    # Determine given_at time - strip timezone for naive timestamp column
    given_at = dose_in.given_at or datetime.now(UTC)
    if given_at.tzinfo is not None:
        # Convert to UTC and strip timezone info for naive timestamp storage
        given_at = given_at.astimezone(UTC).replace(tzinfo=None)

    dose = PetMedicationDose(
        medication_id=dose_in.medication_id,
        given_at=given_at,
        given_by=UUID(user_id),
        notes=dose_in.notes,
    )
    db.add(dose)
    await db.commit()
    await db.refresh(dose)

    # Invalidate dashboard cache
    await invalidate_dose_caches(db, dose_in.medication_id)

    # Notify other family members - use friendly_name if set
    display_name = medication.friendly_name or medication.name
    await notify_family_dose_administered(
        db=db,
        family_id=pet.family_id,
        exclude_user_id=UUID(user_id),
        user_name=user_name,
        pet_name=pet.name,
        medication_name=display_name,
    )

    return DoseResponse.model_validate(dose)


async def get_user_name_map(db: AsyncSession, user_ids: set, current_user_id: str) -> Dict[str, str]:
    """Build a map of user IDs to formatted names."""
    user_name_map: Dict[str, str] = {}
    if user_ids:
        users_query = select(User).where(User.id.in_(list(user_ids)))
        users_result = await db.execute(users_query)
        for user in users_result.scalars().all():
            user_id_str = str(user.id)
            if user_id_str == current_user_id:
                user_name_map[user_id_str] = "You"
            else:
                user_name_map[user_id_str] = format_user_name(user.first_name, user.last_name)
    return user_name_map


@router.get("/medication/{medication_id}", response_model=DoseListResponse)
async def list_doses(
    medication_id: UUID,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List doses for a medication with pagination."""
    # Verify user has access to this medication through family membership
    await verify_medication_access(db, user_id, medication_id)

    # Get total count for pagination
    count_query = select(func.count()).where(PetMedicationDose.medication_id == medication_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = (
        select(PetMedicationDose)
        .where(PetMedicationDose.medication_id == medication_id)
        .order_by(PetMedicationDose.given_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    doses = result.scalars().all()

    # Get user names for all doses
    user_ids = {d.given_by for d in doses if d.given_by}
    user_name_map = await get_user_name_map(db, user_ids, user_id)

    # Build responses with formatted names
    dose_responses = []
    for d in doses:
        dose_dict = {
            "id": d.id,
            "medication_id": d.medication_id,
            "given_at": d.given_at,
            "given_by": user_name_map.get(str(d.given_by), "Unknown"),
            "notes": d.notes,
            "created_at": d.created_at,
        }
        dose_responses.append(DoseDetailResponse.model_validate(dose_dict))

    return DoseListResponse(doses=dose_responses, total=total)


@router.get("/medication/{medication_id}/today", response_model=DoseListResponse)
async def get_today_doses(
    medication_id: UUID,
    timezone: str = "UTC",
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get today's doses for a medication.

    Args:
        timezone: IANA timezone identifier (e.g., "America/Los_Angeles")
                  Used to calculate "today" in the user's local timezone.
    """
    # Verify user has access to this medication through family membership
    await verify_medication_access(db, user_id, medication_id)

    # Parse timezone, fallback to UTC if invalid
    try:
        tz = ZoneInfo(timezone)
        tz_str = timezone
    except Exception:
        tz = ZoneInfo("UTC")
        tz_str = "UTC"

    # Get current time in UTC and convert to user's timezone
    now_utc = datetime.now(dt_timezone.utc)
    now_local = now_utc.astimezone(tz)

    # Calculate today's boundaries in user's local timezone
    today_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_date_str = today_local.date().isoformat()

    # Check cache first
    cache_key = key_today_doses(str(medication_id), today_date_str, tz_str)
    cached = await cache_get(cache_key, DoseListResponse)
    if cached:
        return cached

    tomorrow_local = today_local + timedelta(days=1)

    # Convert back to naive UTC datetimes for database queries
    today = today_local.astimezone(dt_timezone.utc).replace(tzinfo=None)
    tomorrow = tomorrow_local.astimezone(dt_timezone.utc).replace(tzinfo=None)

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

    # Get user names for all doses
    user_ids = {d.given_by for d in doses if d.given_by}
    user_name_map = await get_user_name_map(db, user_ids, user_id)

    # Build responses with formatted names
    dose_responses = []
    for d in doses:
        dose_dict = {
            "id": d.id,
            "medication_id": d.medication_id,
            "given_at": d.given_at,
            "given_by": user_name_map.get(str(d.given_by), "Unknown"),
            "notes": d.notes,
            "created_at": d.created_at,
        }
        dose_responses.append(DoseDetailResponse.model_validate(dose_dict))

    response = DoseListResponse(doses=dose_responses)

    # Cache the result
    await cache_set(cache_key, response, TTL_DOSE_COUNTS)

    return response


@router.get("/medication/{medication_id}/last", response_model=DoseDetailResponse)
async def get_last_dose(
    medication_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get the most recent dose for a medication."""
    # Verify user has access to this medication through family membership
    await verify_medication_access(db, user_id, medication_id)

    # Check cache first
    cache_key = key_last_dose(str(medication_id))
    cached = await cache_get(cache_key, DoseDetailResponse)
    if cached:
        return cached

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

    # Get user name
    user_name_map = await get_user_name_map(db, {dose.given_by}, user_id)
    dose_dict = {
        "id": dose.id,
        "medication_id": dose.medication_id,
        "given_at": dose.given_at,
        "given_by": user_name_map.get(str(dose.given_by), "Unknown"),
        "notes": dose.notes,
        "created_at": dose.created_at,
    }
    response = DoseDetailResponse.model_validate(dose_dict)

    # Cache the result
    await cache_set(cache_key, response, TTL_LAST_DOSE)

    return response


@router.delete("/{dose_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dose(
    dose_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a dose record."""
    # Verify user has access to this dose through family membership
    dose = await verify_dose_access(db, user_id, dose_id)
    medication_id = dose.medication_id

    await db.delete(dose)
    await db.commit()

    # Invalidate dashboard cache
    await invalidate_dose_caches(db, medication_id)


@router.patch("/{dose_id}", response_model=DoseDetailResponse)
async def update_dose(
    dose_id: UUID,
    dose_in: DoseUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update a dose record."""
    # Verify user has access to this dose through family membership
    dose = await verify_dose_access(db, user_id, dose_id)

    update_data = dose_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(dose, field, value)

    await db.commit()
    await db.refresh(dose)

    # Invalidate dashboard cache
    await invalidate_dose_caches(db, dose.medication_id)

    # Get user name
    user_name_map = await get_user_name_map(db, {dose.given_by}, user_id)
    dose_dict = {
        "id": dose.id,
        "medication_id": dose.medication_id,
        "given_at": dose.given_at,
        "given_by": user_name_map.get(str(dose.given_by), "Unknown"),
        "notes": dose.notes,
        "created_at": dose.created_at,
    }
    return DoseDetailResponse.model_validate(dose_dict)


@router.get("/all/{pet_id}", response_model=AllDosesListResponse)
async def list_all_doses(
    pet_id: UUID,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all doses across all medications for a pet (for history view).

    Returns doses with medication info included, sorted by given_at descending.
    Includes doses from archived medications to preserve history.
    """
    # Verify user has access to this pet through family membership
    await verify_pet_access(db, user_id, pet_id)

    # Get all medication IDs for this pet (including archived for history)
    meds_query = select(
        PetMedication.id,
        PetMedication.name,
        PetMedication.friendly_name,
    ).where(PetMedication.pet_id == pet_id)
    meds_result = await db.execute(meds_query)
    # Use friendly_name if set, otherwise use name
    medications = {
        row.id: row.friendly_name or row.name
        for row in meds_result.all()
    }
    medication_ids = list(medications.keys())

    if not medication_ids:
        return AllDosesListResponse(doses=[], total=0)

    # Count total doses
    count_query = select(func.count()).select_from(PetMedicationDose).where(
        PetMedicationDose.medication_id.in_(medication_ids)
    )
    total = (await db.execute(count_query)).scalar() or 0

    # Get doses with pagination
    query = (
        select(PetMedicationDose)
        .where(PetMedicationDose.medication_id.in_(medication_ids))
        .order_by(PetMedicationDose.given_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    doses = result.scalars().all()

    # Get user names for all doses
    user_ids = {d.given_by for d in doses if d.given_by}
    user_name_map = await get_user_name_map(db, user_ids, user_id)

    # Build responses with medication info and formatted names
    dose_responses = []
    for d in doses:
        dose_dict = {
            "id": d.id,
            "medication_id": d.medication_id,
            "medication_name": medications.get(d.medication_id, "Unknown"),
            "pet_id": pet_id,
            "given_at": d.given_at,
            "given_by": user_name_map.get(str(d.given_by), "Unknown"),
            "notes": d.notes,
            "created_at": d.created_at,
        }
        dose_responses.append(AllDoseDetailResponse.model_validate(dose_dict))

    return AllDosesListResponse(doses=dose_responses, total=total)
