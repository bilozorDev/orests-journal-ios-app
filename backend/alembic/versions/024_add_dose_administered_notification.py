"""Add dose_administered notification preference

Revision ID: 024
Revises: 023
Create Date: 2025-12-29

Adds dose_administered preference to notification_preferences table
so users can opt-out of notifications when family members record doses.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '024'
down_revision: Union[str, None] = '023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'notification_preferences',
        sa.Column('dose_administered', sa.Boolean, nullable=False, server_default='true')
    )


def downgrade() -> None:
    op.drop_column('notification_preferences', 'dose_administered')
