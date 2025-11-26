"""add_fk_constraints

Revision ID: 007
Revises: 006
Create Date: 2025-11-25

Converts org_id and created_by columns from VARCHAR to UUID and adds
proper foreign key constraints for referential integrity.

This migration:
1. Converts pets.org_id from VARCHAR to UUID with FK to families
2. Converts pet_foods.org_id from VARCHAR to UUID with FK to families
3. Converts created_by columns to UUID with FK to users

NOTE: This migration assumes all existing data has valid UUID strings.
Run data validation before applying in production.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================
    # DROP RLS POLICIES THAT DEPEND ON ORG_ID
    # ============================================
    # These policies reference org_id::uuid and must be dropped before
    # we can modify the org_id column. We'll recreate them after.

    op.execute("DROP POLICY IF EXISTS pet_health_events_access ON pet_health_events")
    op.execute("DROP POLICY IF EXISTS pet_medication_doses_access ON pet_medication_doses")
    op.execute("DROP POLICY IF EXISTS pet_health_categories_pet_access ON pet_health_categories")
    op.execute("DROP POLICY IF EXISTS pet_medications_pet_access ON pet_medications")
    op.execute("DROP POLICY IF EXISTS pet_calorie_goals_pet_access ON pet_calorie_goals")
    op.execute("DROP POLICY IF EXISTS pet_feedings_pet_access ON pet_feedings")
    op.execute("DROP POLICY IF EXISTS health_records_pet_access ON health_records")
    op.execute("DROP POLICY IF EXISTS pet_foods_family_access ON pet_foods")
    op.execute("DROP POLICY IF EXISTS pets_family_access ON pets")

    # ============================================
    # PETS TABLE - org_id to UUID with FK
    # ============================================

    # Drop the existing index on org_id
    op.drop_index('ix_pets_org_id', table_name='pets')

    # Add new family_id column as UUID
    op.add_column('pets', sa.Column('family_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Copy data from org_id to family_id (casting string to UUID)
    op.execute("UPDATE pets SET family_id = org_id::uuid WHERE org_id IS NOT NULL")

    # Make family_id NOT NULL after data migration
    op.alter_column('pets', 'family_id', nullable=False)

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_pets_family_id',
        'pets', 'families',
        ['family_id'], ['id'],
        ondelete='CASCADE'
    )

    # Create index on new column
    op.create_index('ix_pets_family_id', 'pets', ['family_id'])

    # Drop old org_id column
    op.drop_column('pets', 'org_id')

    # Rename family_id to org_id
    op.alter_column('pets', 'family_id', new_column_name='org_id')

    # Rename the index and FK constraint
    op.drop_index('ix_pets_family_id', table_name='pets')
    op.create_index('ix_pets_org_id', 'pets', ['org_id'])

    # ============================================
    # PET_FOODS TABLE - org_id to UUID with FK
    # ============================================

    # Drop the existing index
    op.drop_index('ix_pet_foods_org_id', table_name='pet_foods')

    # Add new family_id column as UUID
    op.add_column('pet_foods', sa.Column('family_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Copy data from org_id to family_id
    op.execute("UPDATE pet_foods SET family_id = org_id::uuid WHERE org_id IS NOT NULL")

    # Make family_id NOT NULL
    op.alter_column('pet_foods', 'family_id', nullable=False)

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_pet_foods_family_id',
        'pet_foods', 'families',
        ['family_id'], ['id'],
        ondelete='CASCADE'
    )

    # Create index on new column
    op.create_index('ix_pet_foods_family_id', 'pet_foods', ['family_id'])

    # Drop old column
    op.drop_column('pet_foods', 'org_id')

    # Rename family_id to org_id
    op.alter_column('pet_foods', 'family_id', new_column_name='org_id')

    # Rename index
    op.drop_index('ix_pet_foods_family_id', table_name='pet_foods')
    op.create_index('ix_pet_foods_org_id', 'pet_foods', ['org_id'])

    # ============================================
    # PETS TABLE - created_by to UUID with FK
    # ============================================

    # Add new column
    op.add_column('pets', sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Copy data
    op.execute("UPDATE pets SET creator_id = created_by::uuid WHERE created_by IS NOT NULL")

    # Make NOT NULL
    op.alter_column('pets', 'creator_id', nullable=False)

    # Add FK constraint
    op.create_foreign_key(
        'fk_pets_creator_id',
        'pets', 'users',
        ['creator_id'], ['id'],
        ondelete='SET NULL'
    )

    # Drop old column
    op.drop_column('pets', 'created_by')

    # Rename
    op.alter_column('pets', 'creator_id', new_column_name='created_by')

    # ============================================
    # PET_FOODS TABLE - created_by to UUID with FK
    # ============================================

    op.add_column('pet_foods', sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE pet_foods SET creator_id = created_by::uuid WHERE created_by IS NOT NULL")
    op.alter_column('pet_foods', 'creator_id', nullable=False)
    op.create_foreign_key(
        'fk_pet_foods_creator_id',
        'pet_foods', 'users',
        ['creator_id'], ['id'],
        ondelete='SET NULL'
    )
    op.drop_column('pet_foods', 'created_by')
    op.alter_column('pet_foods', 'creator_id', new_column_name='created_by')

    # ============================================
    # PET_FEEDINGS TABLE - fed_by to UUID with FK
    # ============================================

    op.add_column('pet_feedings', sa.Column('feeder_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE pet_feedings SET feeder_id = fed_by::uuid WHERE fed_by IS NOT NULL")
    op.alter_column('pet_feedings', 'feeder_id', nullable=False)
    op.create_foreign_key(
        'fk_pet_feedings_feeder_id',
        'pet_feedings', 'users',
        ['feeder_id'], ['id'],
        ondelete='SET NULL'
    )
    op.drop_column('pet_feedings', 'fed_by')
    op.alter_column('pet_feedings', 'feeder_id', new_column_name='fed_by')

    # ============================================
    # PET_CALORIE_GOALS TABLE - created_by to UUID with FK
    # ============================================

    op.add_column('pet_calorie_goals', sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE pet_calorie_goals SET creator_id = created_by::uuid WHERE created_by IS NOT NULL")
    op.alter_column('pet_calorie_goals', 'creator_id', nullable=False)
    op.create_foreign_key(
        'fk_pet_calorie_goals_creator_id',
        'pet_calorie_goals', 'users',
        ['creator_id'], ['id'],
        ondelete='SET NULL'
    )
    op.drop_column('pet_calorie_goals', 'created_by')
    op.alter_column('pet_calorie_goals', 'creator_id', new_column_name='created_by')

    # ============================================
    # PET_MEDICATIONS TABLE - created_by to UUID with FK
    # ============================================

    op.add_column('pet_medications', sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE pet_medications SET creator_id = created_by::uuid WHERE created_by IS NOT NULL")
    op.alter_column('pet_medications', 'creator_id', nullable=False)
    op.create_foreign_key(
        'fk_pet_medications_creator_id',
        'pet_medications', 'users',
        ['creator_id'], ['id'],
        ondelete='SET NULL'
    )
    op.drop_column('pet_medications', 'created_by')
    op.alter_column('pet_medications', 'creator_id', new_column_name='created_by')

    # ============================================
    # PET_MEDICATION_DOSES TABLE - given_by to UUID with FK
    # ============================================

    op.add_column('pet_medication_doses', sa.Column('giver_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE pet_medication_doses SET giver_id = given_by::uuid WHERE given_by IS NOT NULL")
    op.alter_column('pet_medication_doses', 'giver_id', nullable=False)
    op.create_foreign_key(
        'fk_pet_medication_doses_giver_id',
        'pet_medication_doses', 'users',
        ['giver_id'], ['id'],
        ondelete='SET NULL'
    )
    op.drop_column('pet_medication_doses', 'given_by')
    op.alter_column('pet_medication_doses', 'giver_id', new_column_name='given_by')

    # ============================================
    # PET_HEALTH_CATEGORIES TABLE - created_by to UUID with FK
    # ============================================

    op.add_column('pet_health_categories', sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE pet_health_categories SET creator_id = created_by::uuid WHERE created_by IS NOT NULL")
    op.alter_column('pet_health_categories', 'creator_id', nullable=False)
    op.create_foreign_key(
        'fk_pet_health_categories_creator_id',
        'pet_health_categories', 'users',
        ['creator_id'], ['id'],
        ondelete='SET NULL'
    )
    op.drop_column('pet_health_categories', 'created_by')
    op.alter_column('pet_health_categories', 'creator_id', new_column_name='created_by')

    # ============================================
    # PET_HEALTH_EVENTS TABLE - created_by to UUID with FK
    # ============================================

    op.add_column('pet_health_events', sa.Column('creator_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE pet_health_events SET creator_id = created_by::uuid WHERE created_by IS NOT NULL")
    op.alter_column('pet_health_events', 'creator_id', nullable=False)
    op.create_foreign_key(
        'fk_pet_health_events_creator_id',
        'pet_health_events', 'users',
        ['creator_id'], ['id'],
        ondelete='SET NULL'
    )
    op.drop_column('pet_health_events', 'created_by')
    op.alter_column('pet_health_events', 'creator_id', new_column_name='created_by')

    # ============================================
    # RECREATE RLS POLICIES WITH NATIVE UUID
    # ============================================
    # Now that org_id is a native UUID, we don't need the ::uuid cast

    # Pets: Users can access pets belonging to their families
    op.execute("""
        CREATE POLICY pets_family_access ON pets
            FOR ALL
            USING (org_id IN (SELECT get_user_family_ids()))
            WITH CHECK (org_id IN (SELECT get_user_family_ids()))
    """)

    # Pet Foods: Users can access foods belonging to their families
    op.execute("""
        CREATE POLICY pet_foods_family_access ON pet_foods
            FOR ALL
            USING (org_id IN (SELECT get_user_family_ids()))
            WITH CHECK (org_id IN (SELECT get_user_family_ids()))
    """)

    # Health Records: Users can access health records for their pets
    op.execute("""
        CREATE POLICY health_records_pet_access ON health_records
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Feedings: Users can access feedings for their pets
    op.execute("""
        CREATE POLICY pet_feedings_pet_access ON pet_feedings
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Calorie Goals: Users can access calorie goals for their pets
    op.execute("""
        CREATE POLICY pet_calorie_goals_pet_access ON pet_calorie_goals
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Medications: Users can access medications for their pets
    op.execute("""
        CREATE POLICY pet_medications_pet_access ON pet_medications
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Health Categories: Users can access health categories for their pets
    op.execute("""
        CREATE POLICY pet_health_categories_pet_access ON pet_health_categories
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Medication Doses: Access via medication -> pet -> family
    op.execute("""
        CREATE POLICY pet_medication_doses_access ON pet_medication_doses
            FOR ALL
            USING (medication_id IN (
                SELECT pm.id FROM pet_medications pm
                JOIN pets p ON pm.pet_id = p.id
                WHERE p.org_id IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (medication_id IN (
                SELECT pm.id FROM pet_medications pm
                JOIN pets p ON pm.pet_id = p.id
                WHERE p.org_id IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Health Events: Access via category -> pet -> family
    op.execute("""
        CREATE POLICY pet_health_events_access ON pet_health_events
            FOR ALL
            USING (category_id IN (
                SELECT phc.id FROM pet_health_categories phc
                JOIN pets p ON phc.pet_id = p.id
                WHERE p.org_id IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (category_id IN (
                SELECT phc.id FROM pet_health_categories phc
                JOIN pets p ON phc.pet_id = p.id
                WHERE p.org_id IN (SELECT get_user_family_ids())
            ))
    """)


def downgrade() -> None:
    # This is a complex downgrade - convert UUIDs back to VARCHAR
    # In practice, you would not want to downgrade after this migration
    # as it would lose FK integrity

    # ============================================
    # DROP RLS POLICIES FIRST
    # ============================================
    op.execute("DROP POLICY IF EXISTS pet_health_events_access ON pet_health_events")
    op.execute("DROP POLICY IF EXISTS pet_medication_doses_access ON pet_medication_doses")
    op.execute("DROP POLICY IF EXISTS pet_health_categories_pet_access ON pet_health_categories")
    op.execute("DROP POLICY IF EXISTS pet_medications_pet_access ON pet_medications")
    op.execute("DROP POLICY IF EXISTS pet_calorie_goals_pet_access ON pet_calorie_goals")
    op.execute("DROP POLICY IF EXISTS pet_feedings_pet_access ON pet_feedings")
    op.execute("DROP POLICY IF EXISTS health_records_pet_access ON health_records")
    op.execute("DROP POLICY IF EXISTS pet_foods_family_access ON pet_foods")
    op.execute("DROP POLICY IF EXISTS pets_family_access ON pets")

    # ============================================
    # PET_HEALTH_EVENTS
    # ============================================
    op.drop_constraint('fk_pet_health_events_creator_id', 'pet_health_events', type_='foreignkey')
    op.add_column('pet_health_events', sa.Column('creator_str', sa.String(255), nullable=True))
    op.execute("UPDATE pet_health_events SET creator_str = created_by::text")
    op.drop_column('pet_health_events', 'created_by')
    op.alter_column('pet_health_events', 'creator_str', new_column_name='created_by')
    op.alter_column('pet_health_events', 'created_by', nullable=False)

    # ============================================
    # PET_HEALTH_CATEGORIES
    # ============================================
    op.drop_constraint('fk_pet_health_categories_creator_id', 'pet_health_categories', type_='foreignkey')
    op.add_column('pet_health_categories', sa.Column('creator_str', sa.String(255), nullable=True))
    op.execute("UPDATE pet_health_categories SET creator_str = created_by::text")
    op.drop_column('pet_health_categories', 'created_by')
    op.alter_column('pet_health_categories', 'creator_str', new_column_name='created_by')
    op.alter_column('pet_health_categories', 'created_by', nullable=False)

    # ============================================
    # PET_MEDICATION_DOSES
    # ============================================
    op.drop_constraint('fk_pet_medication_doses_giver_id', 'pet_medication_doses', type_='foreignkey')
    op.add_column('pet_medication_doses', sa.Column('giver_str', sa.String(255), nullable=True))
    op.execute("UPDATE pet_medication_doses SET giver_str = given_by::text")
    op.drop_column('pet_medication_doses', 'given_by')
    op.alter_column('pet_medication_doses', 'giver_str', new_column_name='given_by')
    op.alter_column('pet_medication_doses', 'given_by', nullable=False)

    # ============================================
    # PET_MEDICATIONS
    # ============================================
    op.drop_constraint('fk_pet_medications_creator_id', 'pet_medications', type_='foreignkey')
    op.add_column('pet_medications', sa.Column('creator_str', sa.String(255), nullable=True))
    op.execute("UPDATE pet_medications SET creator_str = created_by::text")
    op.drop_column('pet_medications', 'created_by')
    op.alter_column('pet_medications', 'creator_str', new_column_name='created_by')
    op.alter_column('pet_medications', 'created_by', nullable=False)

    # ============================================
    # PET_CALORIE_GOALS
    # ============================================
    op.drop_constraint('fk_pet_calorie_goals_creator_id', 'pet_calorie_goals', type_='foreignkey')
    op.add_column('pet_calorie_goals', sa.Column('creator_str', sa.String(255), nullable=True))
    op.execute("UPDATE pet_calorie_goals SET creator_str = created_by::text")
    op.drop_column('pet_calorie_goals', 'created_by')
    op.alter_column('pet_calorie_goals', 'creator_str', new_column_name='created_by')
    op.alter_column('pet_calorie_goals', 'created_by', nullable=False)

    # ============================================
    # PET_FEEDINGS
    # ============================================
    op.drop_constraint('fk_pet_feedings_feeder_id', 'pet_feedings', type_='foreignkey')
    op.add_column('pet_feedings', sa.Column('feeder_str', sa.String(255), nullable=True))
    op.execute("UPDATE pet_feedings SET feeder_str = fed_by::text")
    op.drop_column('pet_feedings', 'fed_by')
    op.alter_column('pet_feedings', 'feeder_str', new_column_name='fed_by')
    op.alter_column('pet_feedings', 'fed_by', nullable=False)

    # ============================================
    # PET_FOODS - created_by
    # ============================================
    op.drop_constraint('fk_pet_foods_creator_id', 'pet_foods', type_='foreignkey')
    op.add_column('pet_foods', sa.Column('creator_str', sa.String(255), nullable=True))
    op.execute("UPDATE pet_foods SET creator_str = created_by::text")
    op.drop_column('pet_foods', 'created_by')
    op.alter_column('pet_foods', 'creator_str', new_column_name='created_by')
    op.alter_column('pet_foods', 'created_by', nullable=False)

    # ============================================
    # PETS - created_by
    # ============================================
    op.drop_constraint('fk_pets_creator_id', 'pets', type_='foreignkey')
    op.add_column('pets', sa.Column('creator_str', sa.String(255), nullable=True))
    op.execute("UPDATE pets SET creator_str = created_by::text")
    op.drop_column('pets', 'created_by')
    op.alter_column('pets', 'creator_str', new_column_name='created_by')
    op.alter_column('pets', 'created_by', nullable=False)

    # ============================================
    # PET_FOODS - org_id
    # ============================================
    op.drop_index('ix_pet_foods_org_id', table_name='pet_foods')
    op.drop_constraint('fk_pet_foods_family_id', 'pet_foods', type_='foreignkey')
    op.add_column('pet_foods', sa.Column('org_str', sa.String(255), nullable=True))
    op.execute("UPDATE pet_foods SET org_str = org_id::text")
    op.drop_column('pet_foods', 'org_id')
    op.alter_column('pet_foods', 'org_str', new_column_name='org_id')
    op.alter_column('pet_foods', 'org_id', nullable=False)
    op.create_index('ix_pet_foods_org_id', 'pet_foods', ['org_id'])

    # ============================================
    # PETS - org_id
    # ============================================
    op.drop_index('ix_pets_org_id', table_name='pets')
    op.drop_constraint('fk_pets_family_id', 'pets', type_='foreignkey')
    op.add_column('pets', sa.Column('org_str', sa.String(255), nullable=True))
    op.execute("UPDATE pets SET org_str = org_id::text")
    op.drop_column('pets', 'org_id')
    op.alter_column('pets', 'org_str', new_column_name='org_id')
    op.alter_column('pets', 'org_id', nullable=False)
    op.create_index('ix_pets_org_id', 'pets', ['org_id'])

    # ============================================
    # RECREATE RLS POLICIES WITH ::uuid CAST
    # ============================================
    # After downgrade, org_id is VARCHAR again, so we need the cast

    op.execute("""
        CREATE POLICY pets_family_access ON pets
            FOR ALL
            USING (org_id::uuid IN (SELECT get_user_family_ids()))
            WITH CHECK (org_id::uuid IN (SELECT get_user_family_ids()))
    """)

    op.execute("""
        CREATE POLICY pet_foods_family_access ON pet_foods
            FOR ALL
            USING (org_id::uuid IN (SELECT get_user_family_ids()))
            WITH CHECK (org_id::uuid IN (SELECT get_user_family_ids()))
    """)

    op.execute("""
        CREATE POLICY health_records_pet_access ON health_records
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    op.execute("""
        CREATE POLICY pet_feedings_pet_access ON pet_feedings
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    op.execute("""
        CREATE POLICY pet_calorie_goals_pet_access ON pet_calorie_goals
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    op.execute("""
        CREATE POLICY pet_medications_pet_access ON pet_medications
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

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
        CREATE POLICY pet_medication_doses_access ON pet_medication_doses
            FOR ALL
            USING (medication_id IN (
                SELECT pm.id FROM pet_medications pm
                JOIN pets p ON pm.pet_id = p.id
                WHERE p.org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (medication_id IN (
                SELECT pm.id FROM pet_medications pm
                JOIN pets p ON pm.pet_id = p.id
                WHERE p.org_id::uuid IN (SELECT get_user_family_ids())
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
