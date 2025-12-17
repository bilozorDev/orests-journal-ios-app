"""Add composite index on photos and optimize RLS policy

Revision ID: 020
Revises: 019
Create Date: 2025-12-17

Performance:
- Add composite index on (event_id, sort_order) for efficient photo ordering
- Optimize RLS policy to use EXISTS with JOINs instead of nested subqueries

Data Integrity:
- Add CHECK constraint for non-empty photo_url
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '020'
down_revision: Union[str, None] = '019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PART A: Performance - Composite index for photo ordering
    # This index optimizes queries that fetch photos ordered by sort_order
    op.create_index(
        'ix_pet_health_event_photos_event_sort',
        'pet_health_event_photos',
        ['event_id', 'sort_order']
    )

    # PART B: Optimize RLS policy with EXISTS and JOINs
    # Drop the existing policy and create an optimized version
    op.execute("DROP POLICY IF EXISTS pet_health_event_photos_access ON pet_health_event_photos")

    # Create optimized RLS policy using EXISTS with JOINs (better query plan)
    op.execute("""
        CREATE POLICY pet_health_event_photos_access ON pet_health_event_photos
            FOR ALL
            USING (EXISTS (
                SELECT 1 FROM pet_health_events e
                JOIN pets p ON e.pet_id = p.id
                WHERE e.id = pet_health_event_photos.event_id
                  AND p.org_id IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (EXISTS (
                SELECT 1 FROM pet_health_events e
                JOIN pets p ON e.pet_id = p.id
                WHERE e.id = pet_health_event_photos.event_id
                  AND p.org_id IN (SELECT get_user_family_ids())
            ))
    """)

    # PART C: Data Integrity - CHECK constraint for photo_url
    op.execute("""
        ALTER TABLE pet_health_event_photos
        ADD CONSTRAINT chk_photo_url_not_empty
        CHECK (LENGTH(TRIM(photo_url)) > 0)
    """)


def downgrade() -> None:
    # Remove photo_url CHECK constraint
    op.execute("ALTER TABLE pet_health_event_photos DROP CONSTRAINT IF EXISTS chk_photo_url_not_empty")

    # Restore original RLS policy (nested subqueries version)
    op.execute("DROP POLICY IF EXISTS pet_health_event_photos_access ON pet_health_event_photos")
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

    # Remove composite index
    op.drop_index('ix_pet_health_event_photos_event_sort', 'pet_health_event_photos')
