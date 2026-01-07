"""Add additional performance indexes

Revision ID: 033
Revises: 032
Create Date: 2025-01-06

Adds composite indexes for common query patterns:
- doses: medication_id + given_at for dose history queries
- notification_logs: scheduled_time for duplicate prevention
- family_members: unique constraint on family_id + user_id

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '033'
down_revision: Union[str, None] = '032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Composite index on doses for medication history queries
    op.create_index(
        'ix_pet_medication_doses_med_given',
        'pet_medication_doses',
        ['medication_id', 'given_at'],
        unique=False,
        if_not_exists=True
    )

    # Index on notification_logs.scheduled_time for duplicate prevention
    op.create_index(
        'ix_notification_logs_scheduled_time',
        'notification_logs',
        ['scheduled_time'],
        unique=False,
        if_not_exists=True
    )

    # Unique constraint on family_members to prevent duplicate memberships
    op.create_unique_constraint(
        'uq_family_member',
        'family_members',
        ['family_id', 'user_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_family_member', 'family_members', type_='unique')
    op.drop_index('ix_notification_logs_scheduled_time', table_name='notification_logs')
    op.drop_index('ix_pet_medication_doses_med_given', table_name='pet_medication_doses')
