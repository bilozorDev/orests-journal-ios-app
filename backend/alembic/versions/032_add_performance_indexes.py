"""Add performance indexes for common query patterns

Revision ID: 032
Revises: 031
Create Date: 2025-01-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '032'
down_revision: Union[str, None] = '031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Index on user_device_tokens.user_id for notification lookups
    op.create_index(
        'ix_user_device_tokens_user_id',
        'user_device_tokens',
        ['user_id'],
        unique=False,
        if_not_exists=True
    )

    # Composite index on family_members for role-based queries
    op.create_index(
        'ix_family_members_family_role',
        'family_members',
        ['family_id', 'role'],
        unique=False,
        if_not_exists=True
    )

    # Index on pet_medication_doses.given_at for "today's doses" queries
    op.create_index(
        'ix_pet_medication_doses_given_at',
        'pet_medication_doses',
        ['given_at'],
        unique=False,
        if_not_exists=True
    )

    # Index on pet_feedings.fed_at for date range queries
    op.create_index(
        'ix_pet_feedings_fed_at',
        'pet_feedings',
        ['fed_at'],
        unique=False,
        if_not_exists=True
    )

    # Index on pet_health_events.occurred_at for date filtering
    op.create_index(
        'ix_pet_health_events_occurred_at',
        'pet_health_events',
        ['occurred_at'],
        unique=False,
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index('ix_pet_health_events_occurred_at', table_name='pet_health_events')
    op.drop_index('ix_pet_feedings_fed_at', table_name='pet_feedings')
    op.drop_index('ix_pet_medication_doses_given_at', table_name='pet_medication_doses')
    op.drop_index('ix_family_members_family_role', table_name='family_members')
    op.drop_index('ix_user_device_tokens_user_id', table_name='user_device_tokens')
