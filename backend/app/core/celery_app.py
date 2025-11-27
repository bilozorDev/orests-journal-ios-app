"""
Celery configuration for background task processing.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "orests_journal",
    broker=settings.redis_url or "redis://localhost:6379/0",
    backend=settings.redis_url or "redis://localhost:6379/0",
    include=["app.tasks.notifications"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minute hard limit
    task_soft_time_limit=240,  # 4 minute soft limit
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    # Check for scheduled reminders every minute
    "send-scheduled-reminders": {
        "task": "app.tasks.notifications.send_scheduled_reminders",
        "schedule": crontab(minute="*"),  # Every minute
    },
    # Check for missed doses every 15 minutes
    "check-missed-doses": {
        "task": "app.tasks.notifications.check_missed_doses",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
}
