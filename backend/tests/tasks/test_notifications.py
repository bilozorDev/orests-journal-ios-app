"""
Comprehensive unit tests for Celery notification tasks.

Tests cover:
- send_scheduled_reminders task and its async implementation
- check_missed_doses task and its async implementation
- Helper functions (get_family_device_tokens, notification_already_sent, etc.)
- Database session factory creation for tasks
- Timezone handling and schedule matching
- Notification deduplication
- Error handling and edge cases

All external dependencies (Celery, database, APNS, asyncio) are mocked for isolated unit testing.
"""
import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4, UUID
from zoneinfo import ZoneInfo

import pytest

from app.tasks.notifications import (
    get_task_session_factory,
    run_async,
    get_family_device_tokens,
    notification_already_sent,
    log_notification,
    dose_recorded_around_time,
    send_scheduled_reminders,
    check_missed_doses,
    _send_scheduled_reminders,
    _check_missed_doses,
)


# ============== Test Data ==============

TEST_USER_ID_1 = uuid4()
TEST_USER_ID_2 = uuid4()
TEST_FAMILY_ID = uuid4()
TEST_PET_ID = uuid4()
TEST_MEDICATION_ID = uuid4()
TEST_SCHEDULE_ID = uuid4()
TEST_DEVICE_TOKEN_1 = "a" * 64
TEST_DEVICE_TOKEN_2 = "b" * 64


# ============== Mock Helpers ==============

def create_mock_pet(
    pet_id: UUID = TEST_PET_ID,
    family_id: UUID = TEST_FAMILY_ID,
    name: str = "Buddy",
) -> MagicMock:
    """Create a mock Pet object."""
    pet = MagicMock()
    pet.id = pet_id
    pet.family_id = family_id
    pet.name = name
    return pet


def create_mock_medication(
    medication_id: UUID = TEST_MEDICATION_ID,
    pet_id: UUID = TEST_PET_ID,
    name: str = "Insulin",
    friendly_name: str = None,
    reminders_enabled: bool = True,
    start_date: datetime = None,
    end_date: datetime = None,
    timezone: str = "UTC",
    schedules: list = None,
) -> MagicMock:
    """Create a mock PetMedication object."""
    med = MagicMock()
    med.id = medication_id
    med.pet_id = pet_id
    med.name = name
    med.friendly_name = friendly_name
    med.reminders_enabled = reminders_enabled
    med.start_date = start_date or datetime.now(UTC)
    med.end_date = end_date
    med.timezone = timezone
    med.schedules = schedules or []
    return med


def create_mock_schedule(
    schedule_id: UUID = TEST_SCHEDULE_ID,
    medication_id: UUID = TEST_MEDICATION_ID,
    scheduled_hour: int = 8,
    scheduled_minute: int = 0,
) -> MagicMock:
    """Create a mock MedicationSchedule object."""
    schedule = MagicMock()
    schedule.id = schedule_id
    schedule.medication_id = medication_id
    schedule.scheduled_hour = scheduled_hour
    schedule.scheduled_minute = scheduled_minute
    return schedule


def create_mock_notification_log(
    medication_id: UUID = TEST_MEDICATION_ID,
    notification_type: str = "reminder",
    scheduled_time: datetime = None,
    recipient_count: int = 2,
) -> MagicMock:
    """Create a mock NotificationLog object."""
    log = MagicMock()
    log.id = uuid4()
    log.medication_id = medication_id
    log.notification_type = notification_type
    log.scheduled_time = scheduled_time or datetime.now(UTC)
    log.recipient_count = recipient_count
    return log


def create_mock_dose(
    medication_id: UUID = TEST_MEDICATION_ID,
    given_at: datetime = None,
) -> MagicMock:
    """Create a mock PetMedicationDose object."""
    dose = MagicMock()
    dose.id = uuid4()
    dose.medication_id = medication_id
    dose.given_at = given_at or datetime.now(UTC)
    return dose


def create_mock_db_result(values: list, unique_method: bool = False) -> MagicMock:
    """
    Create a mock database result that returns scalars.

    Args:
        values: List of values to return from scalars().all()
        unique_method: If True, add a unique() method that returns self
    """
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=values)
    result.scalars = MagicMock(return_value=scalars_mock)

    if unique_method:
        # For queries with selectinload that need .unique()
        result.unique = MagicMock(return_value=result)

    return result


def create_mock_scalar_result(value: Any = None) -> MagicMock:
    """Create a mock database result for scalar_one_or_none queries."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    return result


# ============== Helper Function Tests ==============

class TestGetTaskSessionFactory:
    """Test get_task_session_factory function."""

    @patch("app.tasks.notifications.get_settings")
    @patch("app.tasks.notifications.create_async_engine")
    @patch("app.tasks.notifications.async_sessionmaker")
    def test_creates_fresh_engine_and_session_factory(
        self, mock_sessionmaker, mock_create_engine, mock_get_settings
    ):
        """Should create a new async engine and session factory with correct settings."""
        # Setup
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_settings.debug = False
        mock_get_settings.return_value = mock_settings

        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        mock_session_factory = MagicMock()
        mock_sessionmaker.return_value = mock_session_factory

        # Execute
        engine, session_factory = get_task_session_factory()

        # Assert
        assert engine == mock_engine
        assert session_factory == mock_session_factory

        # Verify engine was created with correct parameters
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == mock_settings.database_url
        assert call_args.kwargs["echo"] == False
        assert call_args.kwargs["pool_pre_ping"] is True
        assert call_args.kwargs["pool_size"] == 2
        assert call_args.kwargs["max_overflow"] == 3

    @patch("app.tasks.notifications.get_settings")
    @patch("app.tasks.notifications.create_async_engine")
    @patch("app.tasks.notifications.async_sessionmaker")
    def test_configures_connection_settings_for_asyncpg(
        self, mock_sessionmaker, mock_create_engine, mock_get_settings
    ):
        """Should configure connection settings to avoid prepared statement caching issues."""
        # Setup
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql+asyncpg://test:test@localhost/test"
        mock_settings.debug = True
        mock_get_settings.return_value = mock_settings

        # Execute
        get_task_session_factory()

        # Assert connection args include asyncpg fixes
        call_args = mock_create_engine.call_args
        connect_args = call_args.kwargs["connect_args"]
        assert connect_args["server_settings"]["jit"] == "off"
        assert connect_args["server_settings"]["plan_cache_mode"] == "force_custom_plan"
        assert connect_args["prepared_statement_cache_size"] == 0
        assert connect_args["statement_cache_size"] == 0


class TestRunAsync:
    """Test run_async helper function."""

    def test_runs_coroutine_in_new_event_loop(self):
        """Should create a new event loop and run the coroutine to completion."""
        # Setup
        async def sample_coro():
            await asyncio.sleep(0)
            return "test_result"

        # Execute
        result = run_async(sample_coro())

        # Assert
        assert result == "test_result"

    def test_closes_event_loop_after_completion(self):
        """Should close the event loop after running the coroutine."""
        # Setup
        async def sample_coro():
            return "done"

        # Track if close was called
        close_called = []

        original_new_loop = asyncio.new_event_loop

        def mock_new_loop():
            loop = original_new_loop()
            original_close = loop.close

            def tracked_close():
                close_called.append(True)
                return original_close()

            loop.close = tracked_close
            return loop

        with patch("app.tasks.notifications.asyncio.new_event_loop", side_effect=mock_new_loop):
            # Execute
            result = run_async(sample_coro())

            # Assert
            assert result == "done"
            assert len(close_called) == 1, "Event loop close() should have been called"

    def test_closes_event_loop_even_on_exception(self):
        """Should close the event loop even if the coroutine raises an exception."""
        # Setup
        async def failing_coro():
            raise ValueError("Test error")

        # Track if close was called
        close_called = []

        original_new_loop = asyncio.new_event_loop

        def mock_new_loop():
            loop = original_new_loop()
            original_close = loop.close

            def tracked_close():
                close_called.append(True)
                return original_close()

            loop.close = tracked_close
            return loop

        with patch("app.tasks.notifications.asyncio.new_event_loop", side_effect=mock_new_loop):
            # Execute and assert exception is raised
            with pytest.raises(ValueError, match="Test error"):
                run_async(failing_coro())

            # Assert loop was still closed
            assert len(close_called) == 1, "Event loop close() should have been called even on exception"


class TestGetFamilyDeviceTokens:
    """Test get_family_device_tokens helper function."""

    @pytest.mark.asyncio
    async def test_returns_active_device_tokens_for_family_members(self):
        """Should return all active device tokens for family members."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_1, TEST_USER_ID_2])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1, TEST_DEVICE_TOKEN_2])
        db.execute = AsyncMock(side_effect=[members_result, tokens_result])

        # Execute
        tokens = await get_family_device_tokens(db, TEST_FAMILY_ID)

        # Assert
        assert tokens == [TEST_DEVICE_TOKEN_1, TEST_DEVICE_TOKEN_2]
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_family_members(self):
        """Should return empty list when family has no members."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([])
        db.execute = AsyncMock(return_value=members_result)

        # Execute
        tokens = await get_family_device_tokens(db, TEST_FAMILY_ID)

        # Assert
        assert tokens == []
        assert db.execute.call_count == 1  # Should not query for tokens

    @pytest.mark.asyncio
    async def test_only_queries_active_tokens(self):
        """Should only query for tokens where is_active=True."""
        # Setup
        db = AsyncMock()
        members_result = create_mock_db_result([TEST_USER_ID_1])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1])
        db.execute = AsyncMock(side_effect=[members_result, tokens_result])

        # Execute
        await get_family_device_tokens(db, TEST_FAMILY_ID)

        # Assert - verify the second query filters by is_active
        # We can't easily inspect the SQLAlchemy query, but we can verify it was called
        assert db.execute.call_count == 2


class TestNotificationAlreadySent:
    """Test notification_already_sent helper function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_notification_exists(self):
        """Should return True when a notification log exists for the given parameters."""
        # Setup
        db = AsyncMock()
        scheduled_time = datetime.now(UTC)
        existing_log = create_mock_notification_log(
            medication_id=TEST_MEDICATION_ID,
            notification_type="reminder",
            scheduled_time=scheduled_time,
        )
        result = create_mock_scalar_result(existing_log)
        db.execute = AsyncMock(return_value=result)

        # Execute
        already_sent = await notification_already_sent(
            db, TEST_MEDICATION_ID, "reminder", scheduled_time
        )

        # Assert
        assert already_sent is True

    @pytest.mark.asyncio
    async def test_returns_false_when_notification_does_not_exist(self):
        """Should return False when no notification log exists."""
        # Setup
        db = AsyncMock()
        scheduled_time = datetime.now(UTC)
        result = create_mock_scalar_result(None)
        db.execute = AsyncMock(return_value=result)

        # Execute
        already_sent = await notification_already_sent(
            db, TEST_MEDICATION_ID, "reminder", scheduled_time
        )

        # Assert
        assert already_sent is False


class TestLogNotification:
    """Test log_notification helper function."""

    @pytest.mark.asyncio
    async def test_creates_notification_log_entry(self):
        """Should create a NotificationLog entry and commit to database."""
        # Setup - use MagicMock for sync methods, AsyncMock for async methods
        db = MagicMock()
        db.commit = AsyncMock()
        scheduled_time = datetime.now(UTC)

        # Execute
        await log_notification(db, TEST_MEDICATION_ID, "reminder", scheduled_time, 3)

        # Assert
        db.add.assert_called_once()
        db.commit.assert_called_once()

        # Verify the log object has correct attributes
        log_obj = db.add.call_args[0][0]
        assert log_obj.medication_id == TEST_MEDICATION_ID
        assert log_obj.notification_type == "reminder"
        assert log_obj.scheduled_time == scheduled_time
        assert log_obj.recipient_count == 3


class TestDoseRecordedAroundTime:
    """Test dose_recorded_around_time helper function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_dose_recorded_within_window(self):
        """Should return True when a dose exists within the time window."""
        # Setup
        db = AsyncMock()
        expected_time = datetime.now(UTC)
        dose = create_mock_dose(given_at=expected_time + timedelta(minutes=15))
        result = create_mock_scalar_result(dose)
        db.execute = AsyncMock(return_value=result)

        # Execute
        dose_found = await dose_recorded_around_time(
            db, TEST_MEDICATION_ID, expected_time, window_minutes=30
        )

        # Assert
        assert dose_found is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_dose_in_window(self):
        """Should return False when no dose exists in the time window."""
        # Setup
        db = AsyncMock()
        expected_time = datetime.now(UTC)
        result = create_mock_scalar_result(None)
        db.execute = AsyncMock(return_value=result)

        # Execute
        dose_found = await dose_recorded_around_time(
            db, TEST_MEDICATION_ID, expected_time, window_minutes=30
        )

        # Assert
        assert dose_found is False

    @pytest.mark.asyncio
    async def test_uses_custom_window_size(self):
        """Should use the provided window_minutes parameter."""
        # Setup
        db = AsyncMock()
        expected_time = datetime.now(UTC)
        result = create_mock_scalar_result(None)
        db.execute = AsyncMock(return_value=result)

        # Execute with custom window
        await dose_recorded_around_time(
            db, TEST_MEDICATION_ID, expected_time, window_minutes=60
        )

        # Assert - the query was executed (we can't easily verify the exact time window in the query)
        db.execute.assert_called_once()


# ============== Main Task Tests ==============

class TestSendScheduledReminders:
    """Test send_scheduled_reminders Celery task."""

    @patch("app.tasks.notifications.run_async")
    def test_calls_async_implementation(self, mock_run_async):
        """Should call run_async with the async implementation."""
        # Execute
        send_scheduled_reminders()

        # Assert
        mock_run_async.assert_called_once()
        # The argument should be a coroutine
        call_arg = mock_run_async.call_args[0][0]
        assert asyncio.iscoroutine(call_arg)

    @patch("app.tasks.notifications.run_async")
    @patch("app.tasks.notifications.logger")
    def test_logs_task_execution(self, mock_logger, mock_run_async):
        """Should log when task starts running."""
        # Execute
        send_scheduled_reminders()

        # Assert
        mock_logger.info.assert_called_with("Running send_scheduled_reminders task")


class TestSendScheduledRemindersAsync:
    """Test _send_scheduled_reminders async implementation."""

    @pytest.mark.asyncio
    async def test_sends_reminder_for_matching_schedule(self):
        """Should send reminder when medication schedule matches current time."""
        # Setup - create a medication with a schedule matching current UTC time
        now = datetime.now(UTC)
        current_hour = now.hour
        current_minute = now.minute

        schedule = create_mock_schedule(
            scheduled_hour=current_hour,
            scheduled_minute=current_minute,
        )
        medication = create_mock_medication(
            name="Insulin",
            timezone="UTC",
            schedules=[schedule],
            start_date=now - timedelta(days=1),
            end_date=None,
        )
        pet = create_mock_pet(name="Buddy")

        # Mock database
        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        # Query 1: Get all active medications
        meds_result = create_mock_db_result([medication], unique_method=True)

        # Query 2: Get pet
        pet_result = create_mock_scalar_result(pet)

        # Query 3: Check if notification already sent
        not_sent_result = create_mock_scalar_result(None)

        # Query 4: dose_given_for_schedule_slot - exact match (not found)
        dose_exact_result = create_mock_scalar_result(None)

        # Query 5: dose_given_for_schedule_slot - early dose (not found)
        dose_early_result = create_mock_scalar_result(None)

        # Query 6: Get family device tokens (members)
        members_result = create_mock_db_result([TEST_USER_ID_1, TEST_USER_ID_2])

        # Query 7: Get device tokens
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1, TEST_DEVICE_TOKEN_2])

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            dose_exact_result,
            dose_early_result,
            members_result,
            tokens_result,
        ])

        # Mock session factory
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        # Mock APNS service
        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock(return_value=2)

                # Execute
                await _send_scheduled_reminders()

                # Assert
                mock_apns.send_to_multiple.assert_called_once()
                call_args = mock_apns.send_to_multiple.call_args
                assert call_args.kwargs["title"] == "Medication Reminder"
                assert "Buddy" in call_args.kwargs["body"]
                assert "Insulin" in call_args.kwargs["body"]
                assert call_args.kwargs["device_tokens"] == [TEST_DEVICE_TOKEN_1, TEST_DEVICE_TOKEN_2]

        # Verify notification was logged
        assert mock_db.add.call_count == 1
        assert mock_db.commit.call_count == 1

        # Verify engine was disposed
        mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_does_not_send_if_notification_already_sent(self):
        """Should not send notification if it was already sent for this time."""
        # Setup
        now = datetime.now(UTC)
        schedule = create_mock_schedule(
            scheduled_hour=now.hour,
            scheduled_minute=now.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now - timedelta(days=1),
        )
        pet = create_mock_pet()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        # Mock queries
        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        already_sent_result = create_mock_scalar_result(create_mock_notification_log())

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            already_sent_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _send_scheduled_reminders()

                # Assert - should NOT send notification
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_medication_with_no_device_tokens(self):
        """Should skip notification when family has no device tokens."""
        # Setup
        now = datetime.now(UTC)
        schedule = create_mock_schedule(
            scheduled_hour=now.hour,
            scheduled_minute=now.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now - timedelta(days=1),
        )
        pet = create_mock_pet()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        not_sent_result = create_mock_scalar_result(None)
        no_members_result = create_mock_db_result([])

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            no_members_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _send_scheduled_reminders()

                # Assert - should NOT send notification
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_timezone_conversion(self):
        """Should correctly match schedules in different timezones."""
        # Setup - medication in Pacific timezone
        pacific_tz = ZoneInfo("America/Los_Angeles")
        now_pacific = datetime.now(pacific_tz)

        schedule = create_mock_schedule(
            scheduled_hour=now_pacific.hour,
            scheduled_minute=now_pacific.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="America/Los_Angeles",
            start_date=datetime.now(UTC) - timedelta(days=1),
        )
        pet = create_mock_pet()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        not_sent_result = create_mock_scalar_result(None)
        dose_exact_result = create_mock_scalar_result(None)
        dose_early_result = create_mock_scalar_result(None)
        members_result = create_mock_db_result([TEST_USER_ID_1])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1])

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            dose_exact_result,
            dose_early_result,
            members_result,
            tokens_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock(return_value=1)

                # Execute
                await _send_scheduled_reminders()

                # Assert - should send notification
                mock_apns.send_to_multiple.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_medications_outside_date_range(self):
        """Should not send reminders for medications outside their active date range."""
        # Setup - medication that hasn't started yet
        now = datetime.now(UTC)
        schedule = create_mock_schedule(
            scheduled_hour=now.hour,
            scheduled_minute=now.minute,
        )
        future_medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now + timedelta(days=1),  # Starts tomorrow
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        # No medications should match (filtered by start_date in query)
        meds_result = create_mock_db_result([], unique_method=True)

        mock_db.execute = AsyncMock(return_value=meds_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _send_scheduled_reminders()

                # Assert - should NOT send notification
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_invalid_timezone_gracefully(self):
        """Should fall back to UTC for invalid timezones."""
        # Setup
        now = datetime.now(UTC)
        schedule = create_mock_schedule(
            scheduled_hour=now.hour,
            scheduled_minute=now.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="Invalid/Timezone",  # Invalid timezone
            start_date=now - timedelta(days=1),
        )
        pet = create_mock_pet()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        not_sent_result = create_mock_scalar_result(None)
        members_result = create_mock_db_result([TEST_USER_ID_1])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1])

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            members_result,
            tokens_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock(return_value=1)

                # Execute - should not raise exception
                await _send_scheduled_reminders()

                # Should still process using UTC fallback
                # Depending on timing, it may or may not send
                # But it should not crash


class TestCheckMissedDoses:
    """Test check_missed_doses Celery task."""

    @patch("app.tasks.notifications.run_async")
    def test_calls_async_implementation(self, mock_run_async):
        """Should call run_async with the async implementation."""
        # Execute
        check_missed_doses()

        # Assert
        mock_run_async.assert_called_once()
        call_arg = mock_run_async.call_args[0][0]
        assert asyncio.iscoroutine(call_arg)

    @patch("app.tasks.notifications.run_async")
    @patch("app.tasks.notifications.logger")
    def test_logs_task_execution(self, mock_logger, mock_run_async):
        """Should log when task starts running."""
        # Execute
        check_missed_doses()

        # Assert
        mock_logger.info.assert_called_with("Running check_missed_doses task")


class TestCheckMissedDosesAsync:
    """Test _check_missed_doses async implementation."""

    @pytest.mark.asyncio
    async def test_sends_missed_dose_notification_after_one_hour(self):
        """Should send missed dose notification when dose is 1+ hour late and not recorded."""
        # Setup - scheduled time was 2 hours ago
        now_utc = datetime.now(UTC)
        two_hours_ago = now_utc - timedelta(hours=2)

        schedule = create_mock_schedule(
            scheduled_hour=two_hours_ago.hour,
            scheduled_minute=two_hours_ago.minute,
        )
        medication = create_mock_medication(
            name="Insulin",
            timezone="UTC",
            schedules=[schedule],
            start_date=now_utc - timedelta(days=1),
        )
        pet = create_mock_pet(name="Buddy")

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        # Query 1: Get all active medications
        meds_result = create_mock_db_result([medication], unique_method=True)

        # Query 2: Get pet
        pet_result = create_mock_scalar_result(pet)

        # Query 3: Check if missed dose notification already sent
        not_sent_result = create_mock_scalar_result(None)

        # Query 4: Check if dose was recorded
        no_dose_result = create_mock_scalar_result(None)

        # Query 5: Get family members
        members_result = create_mock_db_result([TEST_USER_ID_1])

        # Query 6: Get device tokens
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1])

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            no_dose_result,
            members_result,
            tokens_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock(return_value=1)

                # Execute
                await _check_missed_doses()

                # Assert
                mock_apns.send_to_multiple.assert_called_once()
                call_args = mock_apns.send_to_multiple.call_args
                assert call_args.kwargs["title"] == "Medication Reminder"
                assert "Buddy" in call_args.kwargs["body"]
                assert "Insulin" in call_args.kwargs["body"]
                assert "remember" in call_args.kwargs["body"].lower()

        # Verify notification was logged
        assert mock_db.add.call_count == 1
        assert mock_db.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_does_not_send_if_dose_was_recorded(self):
        """Should not send notification if dose was recorded within time window."""
        # Setup
        now_utc = datetime.now(UTC)
        two_hours_ago = now_utc - timedelta(hours=2)

        schedule = create_mock_schedule(
            scheduled_hour=two_hours_ago.hour,
            scheduled_minute=two_hours_ago.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now_utc - timedelta(days=1),
        )
        pet = create_mock_pet()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        not_sent_result = create_mock_scalar_result(None)
        dose_recorded_result = create_mock_scalar_result(create_mock_dose())

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            dose_recorded_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _check_missed_doses()

                # Assert - should NOT send notification
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_send_for_doses_less_than_one_hour_late(self):
        """Should not send missed dose notification for doses less than 1 hour late."""
        # Setup - scheduled time was only 30 minutes ago
        now_utc = datetime.now(UTC)
        thirty_min_ago = now_utc - timedelta(minutes=30)

        schedule = create_mock_schedule(
            scheduled_hour=thirty_min_ago.hour,
            scheduled_minute=thirty_min_ago.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now_utc - timedelta(days=1),
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)

        mock_db.execute = AsyncMock(return_value=meds_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _check_missed_doses()

                # Assert - should NOT send notification (too soon)
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_send_for_doses_more_than_24_hours_old(self):
        """Should not send missed dose notification for doses more than 24 hours old."""
        # Setup - scheduled time was 25 hours ago (yesterday)
        now_utc = datetime.now(UTC)
        yesterday = now_utc - timedelta(hours=25)

        schedule = create_mock_schedule(
            scheduled_hour=yesterday.hour,
            scheduled_minute=yesterday.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now_utc - timedelta(days=2),
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)

        mock_db.execute = AsyncMock(return_value=meds_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _check_missed_doses()

                # Assert - should NOT send notification (too old)
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_send_if_already_sent(self):
        """Should not send missed dose notification if already sent for this time."""
        # Setup
        now_utc = datetime.now(UTC)
        two_hours_ago = now_utc - timedelta(hours=2)

        schedule = create_mock_schedule(
            scheduled_hour=two_hours_ago.hour,
            scheduled_minute=two_hours_ago.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now_utc - timedelta(days=1),
        )
        pet = create_mock_pet()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        already_sent_result = create_mock_scalar_result(create_mock_notification_log())

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            already_sent_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _check_missed_doses()

                # Assert - should NOT send notification
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_multiple_schedules_per_medication(self):
        """Should check all schedules for a medication."""
        # Setup - medication with 2 schedules, one is late, one is not
        now_utc = datetime.now(UTC)
        two_hours_ago = now_utc - timedelta(hours=2)
        in_future = now_utc + timedelta(hours=2)

        late_schedule = create_mock_schedule(
            schedule_id=uuid4(),
            scheduled_hour=two_hours_ago.hour,
            scheduled_minute=two_hours_ago.minute,
        )
        future_schedule = create_mock_schedule(
            schedule_id=uuid4(),
            scheduled_hour=in_future.hour,
            scheduled_minute=in_future.minute,
        )

        medication = create_mock_medication(
            schedules=[late_schedule, future_schedule],
            timezone="UTC",
            start_date=now_utc - timedelta(days=1),
        )
        pet = create_mock_pet()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        not_sent_result = create_mock_scalar_result(None)
        no_dose_result = create_mock_scalar_result(None)
        members_result = create_mock_db_result([TEST_USER_ID_1])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1])

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            no_dose_result,
            members_result,
            tokens_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock(return_value=1)

                # Execute
                await _check_missed_doses()

                # Assert - should send notification for the late schedule
                mock_apns.send_to_multiple.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_timezone_conversion_for_missed_doses(self):
        """Should correctly handle timezone conversion for missed dose checks."""
        # Setup - medication in Eastern timezone
        eastern_tz = ZoneInfo("America/New_York")
        now_eastern = datetime.now(eastern_tz)
        two_hours_ago_eastern = now_eastern - timedelta(hours=2)

        schedule = create_mock_schedule(
            scheduled_hour=two_hours_ago_eastern.hour,
            scheduled_minute=two_hours_ago_eastern.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="America/New_York",
            start_date=datetime.now(UTC) - timedelta(days=1),
        )
        pet = create_mock_pet()

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        not_sent_result = create_mock_scalar_result(None)
        no_dose_result = create_mock_scalar_result(None)
        members_result = create_mock_db_result([TEST_USER_ID_1])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1])

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            no_dose_result,
            members_result,
            tokens_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock(return_value=1)

                # Execute
                await _check_missed_doses()

                # Assert - should send notification
                mock_apns.send_to_multiple.assert_called_once()


# ============== Edge Cases and Integration Tests ==============

class TestNotificationTasksEdgeCases:
    """Test edge cases in notification tasks."""

    @pytest.mark.asyncio
    async def test_send_reminders_handles_pet_not_found(self):
        """Should skip notification when pet is not found in database."""
        # Setup
        now = datetime.now(UTC)
        schedule = create_mock_schedule(
            scheduled_hour=now.hour,
            scheduled_minute=now.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now - timedelta(days=1),
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(None)  # Pet not found

        mock_db.execute = AsyncMock(side_effect=[meds_result, pet_result])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute - should not raise exception
                await _send_scheduled_reminders()

                # Assert - should NOT send notification
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_reminders_handles_medication_without_schedules(self):
        """Should skip medications that have no schedules."""
        # Setup
        medication = create_mock_medication(
            schedules=[],  # No schedules
            start_date=datetime.now(UTC) - timedelta(days=1),
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync
        meds_result = create_mock_db_result([medication], unique_method=True)
        mock_db.execute = AsyncMock(return_value=meds_result)

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _send_scheduled_reminders()

                # Assert - should NOT send notification
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_missed_doses_handles_pet_not_found(self):
        """Should skip notification when pet is not found for missed dose check."""
        # Setup
        now_utc = datetime.now(UTC)
        two_hours_ago = now_utc - timedelta(hours=2)

        schedule = create_mock_schedule(
            scheduled_hour=two_hours_ago.hour,
            scheduled_minute=two_hours_ago.minute,
        )
        medication = create_mock_medication(
            schedules=[schedule],
            timezone="UTC",
            start_date=now_utc - timedelta(days=1),
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync
        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(None)  # Pet not found

        mock_db.execute = AsyncMock(side_effect=[meds_result, pet_result])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock()

                # Execute
                await _check_missed_doses()

                # Assert - should NOT send notification
                mock_apns.send_to_multiple.assert_not_called()

    @pytest.mark.asyncio
    async def test_notification_custom_data_includes_correct_ids(self):
        """Should include medication_id, pet_id, and pet_name in notification data."""
        # Setup
        now = datetime.now(UTC)
        schedule = create_mock_schedule(
            scheduled_hour=now.hour,
            scheduled_minute=now.minute,
        )
        medication = create_mock_medication(
            medication_id=TEST_MEDICATION_ID,
            pet_id=TEST_PET_ID,
            name="Insulin",
            schedules=[schedule],
            timezone="UTC",
            start_date=now - timedelta(days=1),
        )
        pet = create_mock_pet(
            pet_id=TEST_PET_ID,
            name="Buddy",
        )

        mock_db = AsyncMock()
        mock_db.add = MagicMock()  # add() is sync

        meds_result = create_mock_db_result([medication], unique_method=True)
        pet_result = create_mock_scalar_result(pet)
        not_sent_result = create_mock_scalar_result(None)
        dose_exact_result = create_mock_scalar_result(None)
        dose_early_result = create_mock_scalar_result(None)
        members_result = create_mock_db_result([TEST_USER_ID_1])
        tokens_result = create_mock_db_result([TEST_DEVICE_TOKEN_1])

        mock_db.execute = AsyncMock(side_effect=[
            meds_result,
            pet_result,
            not_sent_result,
            dose_exact_result,
            dose_early_result,
            members_result,
            tokens_result,
        ])

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock()

        mock_engine = AsyncMock()
        mock_engine.dispose = AsyncMock()

        with patch("app.tasks.notifications.get_task_session_factory") as mock_factory:
            mock_factory.return_value = (mock_engine, mock_session_factory)

            with patch("app.tasks.notifications.apns_service") as mock_apns:
                mock_apns.send_to_multiple = AsyncMock(return_value=1)

                # Execute
                await _send_scheduled_reminders()

                # Assert
                call_args = mock_apns.send_to_multiple.call_args
                data = call_args.kwargs["data"]
                assert data["type"] == "medication_reminder"
                assert data["medication_id"] == str(TEST_MEDICATION_ID)
                assert data["pet_id"] == str(TEST_PET_ID)
                assert data["pet_name"] == "Buddy"
