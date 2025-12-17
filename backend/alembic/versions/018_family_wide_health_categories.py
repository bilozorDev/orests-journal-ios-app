"""Make health categories family-wide instead of per-pet

Revision ID: 018
Revises: 017
Create Date: 2025-12-15

Changes pet_health_categories from per-pet to per-family (org_id).
Merges duplicate categories across pets in the same family.
Adds pet_id to events to track which pet the event belongs to.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '018'
down_revision: Union[str, None] = '017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PART A: Add pet_id to events BEFORE we remove it from categories
    # Step A1: Add pet_id column to events (nullable initially)
    op.add_column(
        'pet_health_events',
        sa.Column('pet_id', UUID(as_uuid=True), nullable=True)
    )

    # Step A2: Populate pet_id from category's pet_id (before we change categories)
    op.execute("""
        UPDATE pet_health_events e
        SET pet_id = c.pet_id
        FROM pet_health_categories c
        WHERE e.category_id = c.id
    """)

    # Step A3: Make pet_id NOT NULL
    op.alter_column('pet_health_events', 'pet_id', nullable=False)

    # Step A4: Add foreign key for pet_id on events
    op.create_foreign_key(
        'fk_pet_health_events_pet_id',
        'pet_health_events',
        'pets',
        ['pet_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Step A5: Create index on pet_id for faster lookups
    op.create_index(
        'ix_pet_health_events_pet_id',
        'pet_health_events',
        ['pet_id']
    )

    # PART B: Make categories family-wide
    # Step B1: Add org_id column to categories (nullable initially)
    op.add_column(
        'pet_health_categories',
        sa.Column('org_id', UUID(as_uuid=True), nullable=True)
    )

    # Step B2: Populate org_id from the pet's org_id
    op.execute("""
        UPDATE pet_health_categories c
        SET org_id = p.org_id
        FROM pets p
        WHERE c.pet_id = p.id
    """)

    # Step B3: Merge duplicate categories within each family
    # First, reassign events from duplicate categories to the survivor (oldest category)
    op.execute("""
        WITH category_ranking AS (
            SELECT
                id,
                org_id,
                name_normalized,
                ROW_NUMBER() OVER (
                    PARTITION BY org_id, name_normalized
                    ORDER BY created_at ASC
                ) as rn
            FROM pet_health_categories
        ),
        survivors AS (
            SELECT id, org_id, name_normalized
            FROM category_ranking
            WHERE rn = 1
        ),
        duplicates_mapping AS (
            SELECT
                cr.id as duplicate_id,
                s.id as survivor_id
            FROM category_ranking cr
            JOIN survivors s ON cr.org_id = s.org_id
                AND cr.name_normalized = s.name_normalized
            WHERE cr.rn > 1
        )
        UPDATE pet_health_events e
        SET category_id = dm.survivor_id
        FROM duplicates_mapping dm
        WHERE e.category_id = dm.duplicate_id
    """)

    # Step B4: Delete duplicate categories (keep oldest per org_id + name_normalized)
    op.execute("""
        DELETE FROM pet_health_categories
        WHERE id IN (
            SELECT id FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY org_id, name_normalized
                        ORDER BY created_at ASC
                    ) as rn
                FROM pet_health_categories
            ) ranked
            WHERE rn > 1
        )
    """)

    # Step B5: Make org_id NOT NULL
    op.alter_column('pet_health_categories', 'org_id', nullable=False)

    # Step B6: Add foreign key constraint for org_id
    op.create_foreign_key(
        'fk_pet_health_categories_org_id',
        'pet_health_categories',
        'families',
        ['org_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Step B7: Add unique constraint on (org_id, name_normalized)
    op.create_unique_constraint(
        'uq_pet_health_categories_org_name',
        'pet_health_categories',
        ['org_id', 'name_normalized']
    )

    # Step B8: Create index on org_id for faster lookups
    op.create_index(
        'ix_pet_health_categories_org_id',
        'pet_health_categories',
        ['org_id']
    )

    # Step B9: Drop RLS policies that depend on pet_id before dropping the column
    op.execute("DROP POLICY IF EXISTS pet_health_categories_pet_access ON pet_health_categories")
    op.execute("DROP POLICY IF EXISTS pet_health_events_access ON pet_health_events")

    # Step B10: Drop old pet_id foreign key and column from categories
    op.drop_constraint('pet_health_categories_pet_id_fkey', 'pet_health_categories', type_='foreignkey')
    op.drop_column('pet_health_categories', 'pet_id')

    # Step B11: Recreate RLS policies with new structure
    # Categories now use org_id directly (like pets table)
    op.execute("""
        CREATE POLICY pet_health_categories_family_access ON pet_health_categories
            FOR ALL
            USING (org_id IN (SELECT get_user_family_ids()))
            WITH CHECK (org_id IN (SELECT get_user_family_ids()))
    """)

    # Events now have pet_id directly (like health_records table)
    op.execute("""
        CREATE POLICY pet_health_events_pet_access ON pet_health_events
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)


def downgrade() -> None:
    # Drop new RLS policies first
    op.execute("DROP POLICY IF EXISTS pet_health_categories_family_access ON pet_health_categories")
    op.execute("DROP POLICY IF EXISTS pet_health_events_pet_access ON pet_health_events")

    # PART B: Restore pet_id on categories
    # Re-add pet_id column
    op.add_column(
        'pet_health_categories',
        sa.Column('pet_id', UUID(as_uuid=True), nullable=True)
    )

    # We can't perfectly restore pet_id since categories are now family-wide
    # Assign to the first pet in each family as a fallback
    op.execute("""
        UPDATE pet_health_categories c
        SET pet_id = (
            SELECT p.id
            FROM pets p
            WHERE p.org_id = c.org_id
            ORDER BY p.created_at ASC
            LIMIT 1
        )
    """)

    # Make pet_id NOT NULL
    op.alter_column('pet_health_categories', 'pet_id', nullable=False)

    # Add foreign key for pet_id
    op.create_foreign_key(
        'pet_health_categories_pet_id_fkey',
        'pet_health_categories',
        'pets',
        ['pet_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Drop org_id constraints and column
    op.drop_index('ix_pet_health_categories_org_id', 'pet_health_categories')
    op.drop_constraint('uq_pet_health_categories_org_name', 'pet_health_categories', type_='unique')
    op.drop_constraint('fk_pet_health_categories_org_id', 'pet_health_categories', type_='foreignkey')
    op.drop_column('pet_health_categories', 'org_id')

    # PART A: Remove pet_id from events
    op.drop_index('ix_pet_health_events_pet_id', 'pet_health_events')
    op.drop_constraint('fk_pet_health_events_pet_id', 'pet_health_events', type_='foreignkey')
    op.drop_column('pet_health_events', 'pet_id')

    # Restore old RLS policies
    op.execute("""
        CREATE POLICY pet_health_categories_pet_access ON pet_health_categories
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    op.execute("""
        CREATE POLICY pet_health_events_access ON pet_health_events
            FOR ALL
            USING (category_id IN (
                SELECT phc.id FROM pet_health_categories phc
                JOIN pets p ON phc.pet_id = p.id
                WHERE p.org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (category_id IN (
                SELECT phc.id FROM pet_health_categories phc
                JOIN pets p ON phc.pet_id = p.id
                WHERE p.org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)
