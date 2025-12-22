"""Drop redundant pet_id index on health events

Revision ID: 022
Revises: 021
Create Date: 2025-12-19

Performance:
- Remove redundant ix_pet_health_events_pet_id index
- The composite index ix_pet_health_events_pet_occurred (pet_id, occurred_at DESC)
  already covers all queries that filter by pet_id, making the single-column index
  redundant and wasteful of storage/insert time
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '022'
down_revision: Union[str, None] = '021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop redundant single-column index since composite index covers it
    op.drop_index('ix_pet_health_events_pet_id', 'pet_health_events')


def downgrade() -> None:
    # Restore the index (though it will be redundant)
    op.create_index(
        'ix_pet_health_events_pet_id',
        'pet_health_events',
        ['pet_id']
    )
