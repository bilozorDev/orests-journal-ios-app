"""Fix RLS policies to use family_id instead of org_id.

Migration 028 renamed org_id to family_id but didn't update the RLS policies.
This migration drops and recreates the affected policies with the correct column name.

Revision ID: 029
Revises: 028
Create Date: 2024-12-30
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop existing policies that reference org_id
    op.execute("DROP POLICY IF EXISTS pets_family_access ON pets")
    op.execute("DROP POLICY IF EXISTS pet_foods_family_access ON pet_foods")
    op.execute("DROP POLICY IF EXISTS health_records_pet_access ON health_records")
    op.execute("DROP POLICY IF EXISTS pet_feedings_pet_access ON pet_feedings")
    op.execute("DROP POLICY IF EXISTS pet_calorie_goals_pet_access ON pet_calorie_goals")
    op.execute("DROP POLICY IF EXISTS pet_medications_pet_access ON pet_medications")
    op.execute("DROP POLICY IF EXISTS pet_health_categories_pet_access ON pet_health_categories")
    op.execute("DROP POLICY IF EXISTS pet_medication_doses_access ON pet_medication_doses")
    op.execute("DROP POLICY IF EXISTS pet_health_events_access ON pet_health_events")

    # Recreate policies with family_id instead of org_id

    # Pets: Users can access pets in their families
    op.execute("""
        CREATE POLICY pets_family_access ON pets
            FOR ALL
            USING (family_id::uuid IN (SELECT get_user_family_ids()))
            WITH CHECK (family_id::uuid IN (SELECT get_user_family_ids()))
    """)

    # Pet Foods: Users can access foods in their families
    op.execute("""
        CREATE POLICY pet_foods_family_access ON pet_foods
            FOR ALL
            USING (family_id::uuid IN (SELECT get_user_family_ids()))
            WITH CHECK (family_id::uuid IN (SELECT get_user_family_ids()))
    """)

    # Health Records: Users can access health records for their pets
    op.execute("""
        CREATE POLICY health_records_pet_access ON health_records
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Feedings: Users can access feedings for their pets
    op.execute("""
        CREATE POLICY pet_feedings_pet_access ON pet_feedings
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Calorie Goals: Users can access calorie goals for their pets
    op.execute("""
        CREATE POLICY pet_calorie_goals_pet_access ON pet_calorie_goals
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Medications: Users can access medications for their pets
    op.execute("""
        CREATE POLICY pet_medications_pet_access ON pet_medications
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Health Categories: Users can access health categories in their families
    op.execute("""
        CREATE POLICY pet_health_categories_pet_access ON pet_health_categories
            FOR ALL
            USING (family_id::uuid IN (SELECT get_user_family_ids()))
            WITH CHECK (family_id::uuid IN (SELECT get_user_family_ids()))
    """)

    # Pet Medication Doses: Access via medication -> pet -> family
    op.execute("""
        CREATE POLICY pet_medication_doses_access ON pet_medication_doses
            FOR ALL
            USING (medication_id IN (
                SELECT m.id FROM pet_medications m
                JOIN pets p ON m.pet_id = p.id
                WHERE p.family_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (medication_id IN (
                SELECT m.id FROM pet_medications m
                JOIN pets p ON m.pet_id = p.id
                WHERE p.family_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    # Pet Health Events: Access via pet -> family
    op.execute("""
        CREATE POLICY pet_health_events_access ON pet_health_events
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE family_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)


def downgrade() -> None:
    # Drop the new policies
    op.execute("DROP POLICY IF EXISTS pets_family_access ON pets")
    op.execute("DROP POLICY IF EXISTS pet_foods_family_access ON pet_foods")
    op.execute("DROP POLICY IF EXISTS health_records_pet_access ON health_records")
    op.execute("DROP POLICY IF EXISTS pet_feedings_pet_access ON pet_feedings")
    op.execute("DROP POLICY IF EXISTS pet_calorie_goals_pet_access ON pet_calorie_goals")
    op.execute("DROP POLICY IF EXISTS pet_medications_pet_access ON pet_medications")
    op.execute("DROP POLICY IF EXISTS pet_health_categories_pet_access ON pet_health_categories")
    op.execute("DROP POLICY IF EXISTS pet_medication_doses_access ON pet_medication_doses")
    op.execute("DROP POLICY IF EXISTS pet_health_events_access ON pet_health_events")

    # Recreate policies with org_id (the old column name)
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
            USING (org_id::uuid IN (SELECT get_user_family_ids()))
            WITH CHECK (org_id::uuid IN (SELECT get_user_family_ids()))
    """)

    op.execute("""
        CREATE POLICY pet_medication_doses_access ON pet_medication_doses
            FOR ALL
            USING (medication_id IN (
                SELECT m.id FROM pet_medications m
                JOIN pets p ON m.pet_id = p.id
                WHERE p.org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (medication_id IN (
                SELECT m.id FROM pet_medications m
                JOIN pets p ON m.pet_id = p.id
                WHERE p.org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)

    op.execute("""
        CREATE POLICY pet_health_events_access ON pet_health_events
            FOR ALL
            USING (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
            WITH CHECK (pet_id IN (
                SELECT id FROM pets WHERE org_id::uuid IN (SELECT get_user_family_ids())
            ))
    """)
