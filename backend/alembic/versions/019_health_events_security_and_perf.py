"""Add RLS policy for health event photos and performance index

Revision ID: 019
Revises: 018
Create Date: 2025-12-17

Security:
- Enable RLS on pet_health_event_photos table
- Add policy to restrict photo access to family members

Performance:
- Add composite index on (pet_id, occurred_at DESC) for efficient event listing

Data Integrity:
- Add CHECK constraints for data validation
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '019'
down_revision: Union[str, None] = '018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PART A: Security - RLS for photos table
    # Enable Row Level Security on photos table
    op.execute("ALTER TABLE pet_health_event_photos ENABLE ROW LEVEL SECURITY")

    # Create RLS policy for photos - access through event -> pet -> family chain
    op.execute("""
        CREATE POLICY pet_health_event_photos_access ON pet_health_event_photos
            FOR ALL
            USING (event_id IN (
                SELECT id FROM pet_health_events WHERE pet_id IN (
                    SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
                )
            ))
            WITH CHECK (event_id IN (
                SELECT id FROM pet_health_events WHERE pet_id IN (
                    SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
                )
            ))
    """)

    # PART B: Performance - Composite index for event listing
    # This index optimizes the common query pattern: filter by pet_id, sort by occurred_at DESC
    op.create_index(
        'ix_pet_health_events_pet_occurred',
        'pet_health_events',
        ['pet_id', sa.text('occurred_at DESC')]
    )

    # Additional index for category + occurred_at queries (already exists from earlier migration)
    # ix_pet_health_events_category_occurred - keeping for category filtering

    # PART C: Data Integrity - CHECK constraints
    # Prevent empty category names
    op.execute("""
        ALTER TABLE pet_health_categories
        ADD CONSTRAINT chk_category_name_not_empty
        CHECK (LENGTH(TRIM(name)) > 0)
    """)

    # Ensure valid photo sort order (non-negative)
    op.execute("""
        ALTER TABLE pet_health_event_photos
        ADD CONSTRAINT chk_sort_order_non_negative
        CHECK (sort_order >= 0)
    """)


def downgrade() -> None:
    # Remove CHECK constraints
    op.execute("ALTER TABLE pet_health_event_photos DROP CONSTRAINT IF EXISTS chk_sort_order_non_negative")
    op.execute("ALTER TABLE pet_health_categories DROP CONSTRAINT IF EXISTS chk_category_name_not_empty")

    # Remove composite index
    op.drop_index('ix_pet_health_events_pet_occurred', 'pet_health_events')

    # Remove RLS policy and disable RLS
    op.execute("DROP POLICY IF EXISTS pet_health_event_photos_access ON pet_health_event_photos")
    op.execute("ALTER TABLE pet_health_event_photos DISABLE ROW LEVEL SECURITY")
