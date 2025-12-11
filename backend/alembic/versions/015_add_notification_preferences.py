"""Add notification_preferences table

Revision ID: 015
Revises: 014
Create Date: 2025-12-11

Adds notification_preferences table for per-user notification settings.
Users can opt-out of specific notification types (family updates, pet updates).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '015'
down_revision: Union[str, None] = '014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),

        # Family Updates
        sa.Column('family_member_joined', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('family_role_changed', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('family_member_left', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('family_member_left_promoted', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('family_account_deleted', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('family_account_deleted_promoted', sa.Boolean(), nullable=False, server_default='true'),

        # Pet Updates
        sa.Column('pet_added', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('pet_updated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('pet_deleted', sa.Boolean(), nullable=False, server_default='true'),

        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_notification_preferences_user_id', 'notification_preferences', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_notification_preferences_user_id', 'notification_preferences')
    op.drop_table('notification_preferences')
