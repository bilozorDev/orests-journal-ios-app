"""Add scheduled_for column to pet_medication_doses.

This column links a dose to a specific scheduled time slot,
allowing accurate tracking when doses are given early or late.

Revision ID: 031
Revises: 030
Create Date: 2025-01-01
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scheduled_for column - nullable since existing doses won't have it
    # and unscheduled/PRN doses don't need it
    op.add_column(
        "pet_medication_doses",
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
    )

    # Add index for efficient queries by scheduled_for
    op.create_index(
        "ix_pet_medication_doses_scheduled_for",
        "pet_medication_doses",
        ["medication_id", "scheduled_for"],
    )


def downgrade() -> None:
    op.drop_index("ix_pet_medication_doses_scheduled_for", table_name="pet_medication_doses")
    op.drop_column("pet_medication_doses", "scheduled_for")
