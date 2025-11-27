"""add_notification_tables

Revision ID: 010
Revises: 009
Create Date: 2025-11-26

Adds tables for push notification support:
- user_device_tokens: Store APNs device tokens per user
- medication_schedules: Store scheduled reminder times per medication
- notification_logs: Track sent notifications to prevent duplicates

Also adds reminders_enabled and timezone columns to pet_medications.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '010'
down_revision: Union[str, None] = '009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_device_tokens table
    op.create_table(
        'user_device_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_token', sa.String(255), nullable=False),
        sa.Column('device_name', sa.String(255), nullable=True),
        sa.Column('platform', sa.String(20), nullable=False, server_default='ios'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_user_device_tokens_user_id', 'user_device_tokens', ['user_id'])
    op.create_index('ix_user_device_tokens_active', 'user_device_tokens', ['is_active'], postgresql_where=sa.text('is_active = true'))
    op.create_unique_constraint('uq_user_device_tokens_user_token', 'user_device_tokens', ['user_id', 'device_token'])

    # Create medication_schedules table
    op.create_table(
        'medication_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('medication_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pet_medications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('scheduled_hour', sa.Integer(), nullable=False),
        sa.Column('scheduled_minute', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint('scheduled_hour >= 0 AND scheduled_hour < 24', name='ck_medication_schedules_hour'),
        sa.CheckConstraint('scheduled_minute >= 0 AND scheduled_minute < 60', name='ck_medication_schedules_minute'),
    )
    op.create_index('ix_medication_schedules_medication_id', 'medication_schedules', ['medication_id'])
    op.create_unique_constraint('uq_medication_schedules_time', 'medication_schedules', ['medication_id', 'scheduled_hour', 'scheduled_minute'])

    # Create notification_logs table
    op.create_table(
        'notification_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('medication_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pet_medications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', sa.String(50), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('recipient_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_notification_logs_medication_sent', 'notification_logs', ['medication_id', 'sent_at'])
    op.create_unique_constraint('uq_notification_logs_unique', 'notification_logs', ['medication_id', 'notification_type', 'scheduled_time'])

    # Add columns to pet_medications
    op.add_column('pet_medications', sa.Column('reminders_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('pet_medications', sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'))


def downgrade() -> None:
    # Remove columns from pet_medications
    op.drop_column('pet_medications', 'timezone')
    op.drop_column('pet_medications', 'reminders_enabled')

    # Drop notification_logs table
    op.drop_constraint('uq_notification_logs_unique', 'notification_logs', type_='unique')
    op.drop_index('ix_notification_logs_medication_sent', 'notification_logs')
    op.drop_table('notification_logs')

    # Drop medication_schedules table
    op.drop_constraint('uq_medication_schedules_time', 'medication_schedules', type_='unique')
    op.drop_index('ix_medication_schedules_medication_id', 'medication_schedules')
    op.drop_table('medication_schedules')

    # Drop user_device_tokens table
    op.drop_constraint('uq_user_device_tokens_user_token', 'user_device_tokens', type_='unique')
    op.drop_index('ix_user_device_tokens_active', 'user_device_tokens')
    op.drop_index('ix_user_device_tokens_user_id', 'user_device_tokens')
    op.drop_table('user_device_tokens')
