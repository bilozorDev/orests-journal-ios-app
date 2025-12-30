"""Add performance indexes for medications and doses.

Revision ID: 027
Revises: 026
Create Date: 2024-12-30

Indexes added:
- ix_pet_medications_pet_archived: Speeds up listing active medications by pet
- ix_pet_medications_pet_dates: Speeds up date range queries for reminders
- ix_pet_medication_doses_med_time: Speeds up dose history and today's doses queries
"""

from alembic import op


revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Index for listing medications by pet with archived filter
    # Used by: GET /medications?pet_id=X (filters out archived by default)
    op.create_index(
        "ix_pet_medications_pet_archived",
        "pet_medications",
        ["pet_id", "is_archived"],
    )

    # Index for date range queries (reminder scheduling)
    # Used by: Celery tasks that find active medications by date range
    op.create_index(
        "ix_pet_medications_pet_dates",
        "pet_medications",
        ["pet_id", "start_date", "end_date"],
    )

    # Index for dose queries by medication and time
    # Used by: GET /doses/today, dose history pagination, missed dose checks
    op.create_index(
        "ix_pet_medication_doses_med_time",
        "pet_medication_doses",
        ["medication_id", "given_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_pet_medication_doses_med_time", table_name="pet_medication_doses")
    op.drop_index("ix_pet_medications_pet_dates", table_name="pet_medications")
    op.drop_index("ix_pet_medications_pet_archived", table_name="pet_medications")
