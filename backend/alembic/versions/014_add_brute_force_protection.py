"""Add brute force protection fields

Revision ID: 014
Revises: 013
Create Date: 2025-12-09

Adds lockout fields to users table, success tracking to invite_attempt_logs,
and creates security_alerts table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision: str = '014'
down_revision: Union[str, None] = '013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add lockout fields to users table
    op.add_column('users', sa.Column('is_locked_out', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('lockout_expires_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('failed_invite_attempts', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('last_failed_invite_at', sa.DateTime(), nullable=True))

    # Add success tracking to invite_attempt_logs
    op.add_column('invite_attempt_logs', sa.Column('was_successful', sa.Boolean(), nullable=False, server_default='false'))

    # Create security_alerts table
    op.create_table('security_alerts',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('alert_metadata', JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_reviewed', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_alerts_created_at', 'security_alerts', ['created_at'], unique=False)
    op.create_index('ix_security_alerts_alert_type', 'security_alerts', ['alert_type'], unique=False)
    op.create_index('ix_security_alerts_is_reviewed', 'security_alerts', ['is_reviewed'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_security_alerts_is_reviewed', table_name='security_alerts')
    op.drop_index('ix_security_alerts_alert_type', table_name='security_alerts')
    op.drop_index('ix_security_alerts_created_at', table_name='security_alerts')
    op.drop_table('security_alerts')

    op.drop_column('invite_attempt_logs', 'was_successful')

    op.drop_column('users', 'last_failed_invite_at')
    op.drop_column('users', 'failed_invite_attempts')
    op.drop_column('users', 'lockout_expires_at')
    op.drop_column('users', 'is_locked_out')
