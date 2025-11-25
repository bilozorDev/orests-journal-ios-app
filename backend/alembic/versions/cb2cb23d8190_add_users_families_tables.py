"""add_users_families_tables

Revision ID: cb2cb23d8190
Revises: 001
Create Date: 2025-11-25 14:13:56.465884

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb2cb23d8190'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('apple_user_id', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_apple_user_id'), 'users', ['apple_user_id'], unique=True)

    # Create families table
    op.create_table('families',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('invite_code', sa.String(length=8), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_families_invite_code'), 'families', ['invite_code'], unique=True)

    # Create invite_attempt_logs table (for brute force protection)
    op.create_table('invite_attempt_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('attempted_code', sa.String(length=8), nullable=False),
        sa.Column('attempted_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invite_attempt_logs_attempted_at'), 'invite_attempt_logs', ['attempted_at'], unique=False)

    # Create family_members table (many-to-many)
    op.create_table('family_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('family_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('family_id', 'user_id', name='uq_family_user')
    )


def downgrade() -> None:
    op.drop_table('family_members')
    op.drop_index(op.f('ix_invite_attempt_logs_attempted_at'), table_name='invite_attempt_logs')
    op.drop_table('invite_attempt_logs')
    op.drop_index(op.f('ix_families_invite_code'), table_name='families')
    op.drop_table('families')
    op.drop_index(op.f('ix_users_apple_user_id'), table_name='users')
    op.drop_table('users')
