"""Rename org_id columns to family_id for semantic clarity.

This migration renames org_id to family_id in:
- pets
- pet_foods
- pet_health_categories

The org_id column was a legacy name from when Clerk organizations were used.
Now that we use families, the column should be named family_id for clarity.

Revision ID: 026
Revises: 025
Create Date: 2024-12-30
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename org_id to family_id in pets table
    op.alter_column("pets", "org_id", new_column_name="family_id")

    # Rename org_id to family_id in pet_foods table
    op.alter_column("pet_foods", "org_id", new_column_name="family_id")

    # Rename org_id to family_id in pet_health_categories table
    op.alter_column("pet_health_categories", "org_id", new_column_name="family_id")

    # Rename indexes to match new column name
    # pets table
    op.execute("ALTER INDEX IF EXISTS ix_pets_org_id RENAME TO ix_pets_family_id")

    # pet_foods table
    op.execute("ALTER INDEX IF EXISTS ix_pet_foods_org_id RENAME TO ix_pet_foods_family_id")

    # pet_health_categories table
    op.execute("ALTER INDEX IF EXISTS ix_pet_health_categories_org_id RENAME TO ix_pet_health_categories_family_id")


def downgrade() -> None:
    # Rename family_id back to org_id in pets table
    op.alter_column("pets", "family_id", new_column_name="org_id")

    # Rename family_id back to org_id in pet_foods table
    op.alter_column("pet_foods", "family_id", new_column_name="org_id")

    # Rename family_id back to org_id in pet_health_categories table
    op.alter_column("pet_health_categories", "family_id", new_column_name="org_id")

    # Rename indexes back
    op.execute("ALTER INDEX IF EXISTS ix_pets_family_id RENAME TO ix_pets_org_id")
    op.execute("ALTER INDEX IF EXISTS ix_pet_foods_family_id RENAME TO ix_pet_foods_org_id")
    op.execute("ALTER INDEX IF EXISTS ix_pet_health_categories_family_id RENAME TO ix_pet_health_categories_org_id")
