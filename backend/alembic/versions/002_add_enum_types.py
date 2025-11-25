"""add_enum_types

Revision ID: 002
Revises: cb2cb23d8190
Create Date: 2025-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = 'cb2cb23d8190'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types - use enum member NAMES (what SQLAlchemy sends by default)
    foodcategory = sa.Enum('DRY', 'WET', 'SNACK', name='foodcategory')
    containerunit = sa.Enum('GRAMS', 'OUNCES', 'KILOGRAMS', 'POUNDS', name='containerunit')

    foodcategory.create(op.get_bind(), checkfirst=True)
    containerunit.create(op.get_bind(), checkfirst=True)

    # Alter pet_foods.category from String to enum
    # Map lowercase values to uppercase enum names
    op.execute("""
        ALTER TABLE pet_foods
        ALTER COLUMN category TYPE foodcategory
        USING CASE category
            WHEN 'dry' THEN 'DRY'::foodcategory
            WHEN 'wet' THEN 'WET'::foodcategory
            WHEN 'snack' THEN 'SNACK'::foodcategory
            ELSE category::foodcategory
        END
    """)

    # Alter pet_foods.container_size_unit from String to enum
    # First drop the default, convert type, then set new default
    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit DROP DEFAULT")
    op.execute("""
        ALTER TABLE pet_foods
        ALTER COLUMN container_size_unit TYPE containerunit
        USING CASE container_size_unit
            WHEN 'g' THEN 'GRAMS'::containerunit
            WHEN 'oz' THEN 'OUNCES'::containerunit
            WHEN 'kg' THEN 'KILOGRAMS'::containerunit
            WHEN 'lb' THEN 'POUNDS'::containerunit
            ELSE container_size_unit::containerunit
        END
    """)
    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit SET DEFAULT 'GRAMS'")

    # Alter pet_feedings.amount_unit from String to enum
    # First drop the default, convert type, then set new default
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit DROP DEFAULT")
    op.execute("""
        ALTER TABLE pet_feedings
        ALTER COLUMN amount_unit TYPE containerunit
        USING CASE amount_unit
            WHEN 'g' THEN 'GRAMS'::containerunit
            WHEN 'oz' THEN 'OUNCES'::containerunit
            WHEN 'kg' THEN 'KILOGRAMS'::containerunit
            WHEN 'lb' THEN 'POUNDS'::containerunit
            ELSE amount_unit::containerunit
        END
    """)
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit SET DEFAULT 'GRAMS'")


def downgrade() -> None:
    # Drop defaults first
    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit DROP DEFAULT")
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit DROP DEFAULT")

    # Revert columns back to String
    op.execute("ALTER TABLE pet_foods ALTER COLUMN category TYPE VARCHAR(50) USING category::VARCHAR(50)")
    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit TYPE VARCHAR(10) USING container_size_unit::VARCHAR(10)")
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit TYPE VARCHAR(10) USING amount_unit::VARCHAR(10)")

    # Set defaults back
    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit SET DEFAULT 'g'")
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit SET DEFAULT 'g'")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS foodcategory")
    op.execute("DROP TYPE IF EXISTS containerunit")
