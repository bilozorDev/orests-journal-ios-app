"""Add unique constraints for MedicationSchedule and NotificationLog.

These constraints prevent:
- Duplicate scheduled times for a medication (same hour:minute)
- Duplicate notification logs for the same medication/type/time

Revision ID: 030
Revises: 029
Create Date: 2024-12-30
"""

from alembic import op


revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, clean up any potential duplicates in medication_schedules
    # Keep the first one (by id) for each medication_id + hour + minute combo
    op.execute("""
        DELETE FROM medication_schedules
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM medication_schedules
            GROUP BY medication_id, scheduled_hour, scheduled_minute
        )
    """)

    # Add unique constraint on medication_schedules
    # Prevents duplicate schedule times for the same medication
    op.create_unique_constraint(
        "uq_medication_schedule_time",
        "medication_schedules",
        ["medication_id", "scheduled_hour", "scheduled_minute"],
    )

    # Clean up any potential duplicates in notification_logs
    # Keep the first one for each medication_id + type + scheduled_time combo
    op.execute("""
        DELETE FROM notification_logs
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM notification_logs
            GROUP BY medication_id, notification_type, scheduled_time
        )
    """)

    # Add unique constraint on notification_logs
    # Prevents duplicate notifications for the same medication/type/time
    op.create_unique_constraint(
        "uq_notification_log_type_time",
        "notification_logs",
        ["medication_id", "notification_type", "scheduled_time"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_notification_log_type_time", "notification_logs", type_="unique")
    op.drop_constraint("uq_medication_schedule_time", "medication_schedules", type_="unique")
