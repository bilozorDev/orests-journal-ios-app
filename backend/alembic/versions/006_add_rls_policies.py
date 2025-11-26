"""add_rls_policies

Revision ID: 006
Revises: 005
Create Date: 2025-11-25

Adds Row-Level Security (RLS) policies for defense-in-depth protection.
RLS provides database-level access control as a safety net in case
application-level authorization has bugs.

IMPORTANT: To use RLS, the application must set the session variable
'app.current_user_id' before executing queries. This is done in the
database session setup.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================
    # ENABLE RLS ON ALL TABLES
    # ============================================

    # Note: We use raw SQL for RLS as SQLAlchemy/Alembic don't have
    # native support for RLS commands

    # Tables with direct org_id (family) relationship
    op.execute("ALTER TABLE pets ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_foods ENABLE ROW LEVEL SECURITY")

    # Tables with pet_id relationship (access via pet -> family)
    op.execute("ALTER TABLE health_records ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_feedings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_calorie_goals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_medications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_health_categories ENABLE ROW LEVEL SECURITY")

    # Tables with medication_id relationship (access via medication -> pet -> family)
    op.execute("ALTER TABLE pet_medication_doses ENABLE ROW LEVEL SECURITY")

    # Tables with category_id relationship (access via category -> pet -> family)
    op.execute("ALTER TABLE pet_health_events ENABLE ROW LEVEL SECURITY")

    # ============================================
    # CREATE HELPER FUNCTION
    # ============================================

    # Function to get current user's family IDs
    op.execute("""
        CREATE OR REPLACE FUNCTION get_user_family_ids()
        RETURNS SETOF UUID AS $$
        BEGIN
            -- Check if the session variable is set
            IF current_setting('app.current_user_id', true) IS NULL
               OR current_setting('app.current_user_id', true) = '' THEN
                RETURN;
            END IF;

            RETURN QUERY
            SELECT family_id
            FROM family_members
            WHERE user_id = current_setting('app.current_user_id')::uuid;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER STABLE;
    """)

    # ============================================
    # RLS POLICIES FOR TABLES WITH ORG_ID
    # ============================================

    # Pets: Users can access pets belonging to their families
    op.execute("""
        CREATE POLICY pets_family_access ON pets
            FOR ALL
            USING (org_id::uuid IN (SELECT get_user_family_ids()))
            WITH CHECK (org_id::uuid IN (SELECT get_user_family_ids()))
    """)

    # Pet Foods: Users can access foods belonging to their families
    op.execute("""
        CREATE POLICY pet_foods_family_access ON pet_foods
            FOR ALL
            USING (org_id::uuid IN (SELECT get_user_family_ids()))
            WITH CHECK (org_id::uuid IN (SELECT get_user_family_ids()))
    """)

    # ============================================
    # RLS POLICIES FOR TABLES WITH PET_ID
    # ============================================

    # Health Records: Users can access health records for their pets
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

    # Pet Feedings: Users can access feedings for their pets
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

    # Pet Calorie Goals: Users can access calorie goals for their pets
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

    # Pet Medications: Users can access medications for their pets
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

    # Pet Health Categories: Users can access health categories for their pets
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

    # ============================================
    # RLS POLICIES FOR NESTED TABLES
    # ============================================

    # Pet Medication Doses: Access via medication -> pet -> family
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

    # Pet Health Events: Access via category -> pet -> family
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


def downgrade() -> None:
    # Drop all policies
    op.execute("DROP POLICY IF EXISTS pet_health_events_access ON pet_health_events")
    op.execute("DROP POLICY IF EXISTS pet_medication_doses_access ON pet_medication_doses")
    op.execute("DROP POLICY IF EXISTS pet_health_categories_pet_access ON pet_health_categories")
    op.execute("DROP POLICY IF EXISTS pet_medications_pet_access ON pet_medications")
    op.execute("DROP POLICY IF EXISTS pet_calorie_goals_pet_access ON pet_calorie_goals")
    op.execute("DROP POLICY IF EXISTS pet_feedings_pet_access ON pet_feedings")
    op.execute("DROP POLICY IF EXISTS health_records_pet_access ON health_records")
    op.execute("DROP POLICY IF EXISTS pet_foods_family_access ON pet_foods")
    op.execute("DROP POLICY IF EXISTS pets_family_access ON pets")

    # Drop helper function
    op.execute("DROP FUNCTION IF EXISTS get_user_family_ids()")

    # Disable RLS on all tables
    op.execute("ALTER TABLE pet_health_events DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_medication_doses DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_health_categories DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_medications DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_calorie_goals DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_feedings DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE health_records DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pet_foods DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pets DISABLE ROW LEVEL SECURITY")
