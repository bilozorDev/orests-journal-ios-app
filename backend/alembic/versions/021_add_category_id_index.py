"""Add index on category_id for health events

Revision ID: 021
Revises: 020
Create Date: 2025-12-17

Performance:
- Add index on category_id for efficient filtering by category
- This supports the common query pattern of filtering events by category
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '021'
down_revision: Union[str, None] = '020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add index on category_id for efficient filtering
    op.create_index(
        'ix_pet_health_events_category_id',
        'pet_health_events',
        ['category_id']
    )


def downgrade() -> None:
    op.drop_index('ix_pet_health_events_category_id', 'pet_health_events')
