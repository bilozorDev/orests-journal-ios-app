"""
Celery tasks for medication reminders and notifications.
"""
import asyncio
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.models.medication import PetMedication, PetMedicationDose
from app.models.notification import MedicationSchedule, NotificationLog, UserDeviceToken
from app.models.pet import Pet
from app.models.user import FamilyMember
from app.services.apns import apns_service

logger = logging.getLogger(__name__)


def get_task_session_factory():
    """
    Get or create the async engine and session factory for Celery tasks.

    Uses NullPool since each Celery task creates a new event loop via run_async(),
    and asyncpg connections are bound to the event loop that created them.
    NullPool creates a fresh connection per request and disposes it immediately,
    avoiding connection pool issues across different event loops.

    The engine is disposed after each task completes to clean up resources.
    """
    settings = get_settings()

    # Use NullPool - creates fresh connection per request, disposed immediately
    # This is the correct approach for Celery tasks with separate event loops
    engine = create_async_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,  # No connection pooling - prevents event loop issues
        connect_args={
            "command_timeout": 30,  # 30 second timeout per command
            "server_settings": {
                "jit": "off",
                "plan_cache_mode": "force_custom_plan",
                "statement_timeout": "30000",  # 30 second statement timeout
            },
            "prepared_statement_cache_size": 0,
            "statement_cache_size": 0,
        },
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return engine, session_factory


def run_async(coro):
    """Run async code in a sync context (Celery tasks)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def get_family_device_tokens(db, family_id: UUID) -> list[str]:
    """Get all active device tokens for family members."""
    # Get all family members
    members_query = select(FamilyMember.user_id).where(FamilyMember.family_id == family_id)
    members_result = await db.execute(members_query)
    user_ids = [m for m in members_result.scalars().all()]

    if not user_ids:
        return []

    # Get active device tokens for these users
    tokens_query = select(UserDeviceToken.device_token).where(
        and_(
            UserDeviceToken.user_id.in_(user_ids),
            UserDeviceToken.is_active == True,
        )
    )
    tokens_result = await db.execute(tokens_query)
    return list(tokens_result.scalars().all())


async def notification_already_sent(
    db, medication_id: UUID, notification_type: str, scheduled_time: datetime
) -> bool:
    """Check if a notification was already sent for this medication/time."""
    query = select(NotificationLog).where(
        and_(
            NotificationLog.medication_id == medication_id,
            NotificationLog.notification_type == notification_type,
            NotificationLog.scheduled_time == scheduled_time,
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def log_notification(
    db, medication_id: UUID, notification_type: str, scheduled_time: datetime, recipient_count: int
):
    """Log a sent notification."""
    log = NotificationLog(
        medication_id=medication_id,
        notification_type=notification_type,
        scheduled_time=scheduled_time,
        recipient_count=recipient_count,
    )
    db.add(log)
    await db.commit()


async def dose_recorded_around_time(
    db, medication_id: UUID, expected_time: datetime, window_minutes: int = 30
) -> bool:
    """Check if a dose was recorded within a time window of the expected time."""
    window_start = expected_time - timedelta(minutes=window_minutes)
    window_end = expected_time + timedelta(minutes=window_minutes)

    query = select(PetMedicationDose).where(
        and_(
            PetMedicationDose.medication_id == medication_id,
            PetMedicationDose.given_at >= window_start,
            PetMedicationDose.given_at <= window_end,
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def dose_given_for_schedule_slot(
    db, medication_id: UUID, scheduled_time: datetime
) -> bool:
    """
    Check if a dose was already given for a specific schedule slot.

    Uses the scheduled_for field for exact matching, with fallback to
    time-window matching for doses recorded without scheduled_for.
    """
    # First check for exact match by scheduled_for (within 1 minute tolerance)
    window_start = scheduled_time - timedelta(minutes=1)
    window_end = scheduled_time + timedelta(minutes=1)

    exact_match_query = select(PetMedicationDose).where(
        and_(
            PetMedicationDose.medication_id == medication_id,
            PetMedicationDose.scheduled_for >= window_start,
            PetMedicationDose.scheduled_for <= window_end,
        )
    )
    result = await db.execute(exact_match_query)
    if result.scalar_one_or_none() is not None:
        return True

    # Fallback: check if dose was given within 2 hours before scheduled time
    # (for doses given early without scheduled_for set)
    early_window_start = scheduled_time - timedelta(hours=2)
    early_dose_query = select(PetMedicationDose).where(
        and_(
            PetMedicationDose.medication_id == medication_id,
            PetMedicationDose.given_at >= early_window_start,
            PetMedicationDose.given_at <= scheduled_time,
            PetMedicationDose.scheduled_for.is_(None),  # Only check doses without scheduled_for
        )
    )
    result = await db.execute(early_dose_query)
    return result.scalar_one_or_none() is not None


@celery_app.task(
    name="app.tasks.notifications.send_scheduled_reminders",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def send_scheduled_reminders():
    """
    Send scheduled medication reminders.

    Runs every minute, checks for medications with scheduled times matching
    the current time (within a 1-minute window).
    """
    logger.info("Running send_scheduled_reminders task")
    run_async(_send_scheduled_reminders())


async def _send_scheduled_reminders():
    """Async implementation of send_scheduled_reminders."""
    engine, session_factory = get_task_session_factory()
    try:
        async with session_factory() as db:
            now_utc = datetime.now(UTC)

            # Get all active medications with reminders enabled
            # We filter by timezone in Python since schedules are stored in local time
            query = (
                select(PetMedication)
                .join(Pet)
                .options(selectinload(PetMedication.schedules))
                .where(
                    and_(
                        PetMedication.reminders_enabled == True,
                        # Active check: within date range
                        PetMedication.start_date <= now_utc,
                        or_(
                            PetMedication.end_date.is_(None),
                            PetMedication.end_date >= now_utc,
                        ),
                    )
                )
            )
            result = await db.execute(query)
            all_medications = result.unique().scalars().all()
            logger.info(f"Found {len(all_medications)} active medications with reminders enabled")

            # Filter medications whose schedule matches the current time in their timezone
            medications = []
            for med in all_medications:
                if not med.schedules:
                    continue

                # Get medication's timezone
                try:
                    tz = ZoneInfo(med.timezone)
                except Exception:
                    tz = ZoneInfo("UTC")

                # Get current time in medication's timezone
                now_local = datetime.now(tz)
                local_hour = now_local.hour
                local_minute = now_local.minute

                # Check if any schedule matches
                for schedule in med.schedules:
                    if schedule.scheduled_hour == local_hour and schedule.scheduled_minute == local_minute:
                        display_name = med.friendly_name or med.name
                        logger.info(f"Medication '{display_name}' matches schedule {local_hour}:{local_minute:02d} in {med.timezone}")
                        medications.append(med)
                        break

            logger.info(f"Found {len(medications)} medications with matching schedules")

            for med in medications:
                # Get pet name for notification
                pet_query = select(Pet).where(Pet.id == med.pet_id)
                pet_result = await db.execute(pet_query)
                pet = pet_result.scalar_one_or_none()

                if not pet:
                    continue

                # Get medication's timezone and current local time
                try:
                    tz = ZoneInfo(med.timezone)
                except Exception:
                    tz = ZoneInfo("UTC")

                now_local = datetime.now(tz)

                # Create scheduled time for today in medication's timezone
                scheduled_time = now_local.replace(
                    hour=now_local.hour,
                    minute=now_local.minute,
                    second=0,
                    microsecond=0,
                )
                # Convert back to UTC for storage
                scheduled_time_utc = scheduled_time.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

                # Check if already sent
                if await notification_already_sent(db, med.id, "reminder", scheduled_time_utc):
                    continue

                # Check if dose was already given for this schedule slot
                if await dose_given_for_schedule_slot(db, med.id, scheduled_time_utc):
                    logger.info(f"Skipping reminder for {display_name} - dose already given for this slot")
                    continue

                # Get family device tokens
                tokens = await get_family_device_tokens(db, pet.family_id)

                if not tokens:
                    logger.info(f"No device tokens for medication {med.id}")
                    continue

                # Send notifications - use friendly_name if set
                display_name = med.friendly_name or med.name
                title = "Medication Reminder"
                body = f"Time to give {pet.name} their {display_name}"

                sent_count = await apns_service.send_to_multiple(
                    device_tokens=tokens,
                    title=title,
                    body=body,
                    data={
                        "type": "medication_reminder",
                        "medication_id": str(med.id),
                        "pet_id": str(pet.id),
                        "pet_name": pet.name,
                    },
                )

                # Log the notification
                await log_notification(db, med.id, "reminder", scheduled_time_utc, sent_count)
                logger.info(f"Sent reminder for {display_name} to {sent_count} devices")
    finally:
        await engine.dispose()


@celery_app.task(
    name="app.tasks.notifications.check_missed_doses",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    max_retries=3,
)
def check_missed_doses():
    """
    Check for missed doses and send reminders.

    Runs every 15 minutes, checks for medications where:
    - Scheduled time was 1+ hour ago today
    - No dose was recorded within 30 minutes of scheduled time
    - No missed dose notification was already sent for this time
    """
    logger.info("Running check_missed_doses task")
    run_async(_check_missed_doses())


async def _check_missed_doses():
    """Async implementation of check_missed_doses."""
    engine, session_factory = get_task_session_factory()
    try:
        async with session_factory() as db:
            now = datetime.now(UTC)

            # Get all active medications with reminders enabled
            query = (
                select(PetMedication)
                .join(Pet)
                .options(selectinload(PetMedication.schedules))
                .where(
                    and_(
                        PetMedication.reminders_enabled == True,
                        # Active check
                        PetMedication.start_date <= now,
                        or_(
                            PetMedication.end_date.is_(None),
                            PetMedication.end_date >= now,
                        ),
                    )
                )
            )
            result = await db.execute(query)
            medications = result.unique().scalars().all()

            for med in medications:
                if not med.schedules:
                    continue

                # Get pet info
                pet_query = select(Pet).where(Pet.id == med.pet_id)
                pet_result = await db.execute(pet_query)
                pet = pet_result.scalar_one_or_none()

                if not pet:
                    continue

                # Get medication's timezone
                try:
                    tz = ZoneInfo(med.timezone)
                except Exception:
                    tz = ZoneInfo("UTC")

                now_local = datetime.now(tz)

                # Check each scheduled time
                for schedule in med.schedules:
                    # Create today's scheduled time in medication's timezone
                    scheduled_local = now_local.replace(
                        hour=schedule.scheduled_hour,
                        minute=schedule.scheduled_minute,
                        second=0,
                        microsecond=0,
                    )

                    # Only check if scheduled time was 1+ hour ago
                    time_since_scheduled = now_local - scheduled_local
                    if time_since_scheduled.total_seconds() < 3600:  # Less than 1 hour
                        continue

                    # Only check today's schedules (not future days)
                    if time_since_scheduled.total_seconds() > 86400:  # More than 24 hours
                        continue

                    # Convert to UTC for database queries
                    scheduled_utc = scheduled_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

                    # Check if already sent missed dose notification
                    if await notification_already_sent(db, med.id, "missed_dose", scheduled_utc):
                        continue

                    # Check if dose was recorded around this time
                    if await dose_recorded_around_time(db, med.id, scheduled_utc):
                        continue

                    # Get family device tokens
                    tokens = await get_family_device_tokens(db, pet.family_id)

                    if not tokens:
                        continue

                    # Send missed dose notification - use friendly_name if set
                    display_name = med.friendly_name or med.name
                    title = "Medication Reminder"
                    body = f"Did you remember to give {pet.name} their {display_name}?"

                    sent_count = await apns_service.send_to_multiple(
                        device_tokens=tokens,
                        title=title,
                        body=body,
                        data={
                            "type": "missed_dose",
                            "medication_id": str(med.id),
                            "pet_id": str(pet.id),
                            "pet_name": pet.name,
                        },
                    )

                    # Log the notification
                    await log_notification(db, med.id, "missed_dose", scheduled_utc, sent_count)
                    logger.info(f"Sent missed dose reminder for {display_name} to {sent_count} devices")
    finally:
        await engine.dispose()
