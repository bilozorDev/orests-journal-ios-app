"""Add photo_url to pet_health_events

Revision ID: 016
Revises: 015
Create Date: 2025-12-11

Adds photo_url column to pet_health_events table for attaching photos
to health events (e.g., blood work results, vet receipts).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016'
down_revision: Union[str, None] = '015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'pet_health_events',
        sa.Column('photo_url', sa.String(512), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('pet_health_events', 'photo_url')
