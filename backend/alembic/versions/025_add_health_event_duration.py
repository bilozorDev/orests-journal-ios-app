"""Add duration_minutes to health events for behavioral tracking.

Revision ID: 025
Revises: 024
Create Date: 2024-12-29
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '025'
down_revision = '024'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add duration_minutes column for tracking behavioral event duration
    op.add_column(
        'pet_health_events',
        sa.Column('duration_minutes', sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('pet_health_events', 'duration_minutes')
