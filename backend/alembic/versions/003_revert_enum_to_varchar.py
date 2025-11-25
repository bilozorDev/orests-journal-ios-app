"""revert_enum_to_varchar

Revision ID: 003
Revises: 002
Create Date: 2025-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop defaults first
    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit DROP DEFAULT")
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit DROP DEFAULT")

    # Revert columns back to VARCHAR, converting uppercase enum values to lowercase
    op.execute("""
        ALTER TABLE pet_foods
        ALTER COLUMN category TYPE VARCHAR(50)
        USING CASE category::text
            WHEN 'DRY' THEN 'dry'
            WHEN 'WET' THEN 'wet'
            WHEN 'SNACK' THEN 'snack'
            ELSE LOWER(category::text)
        END
    """)

    op.execute("""
        ALTER TABLE pet_foods
        ALTER COLUMN container_size_unit TYPE VARCHAR(10)
        USING CASE container_size_unit::text
            WHEN 'GRAMS' THEN 'g'
            WHEN 'OUNCES' THEN 'oz'
            WHEN 'KILOGRAMS' THEN 'kg'
            WHEN 'POUNDS' THEN 'lb'
            ELSE LOWER(container_size_unit::text)
        END
    """)

    op.execute("""
        ALTER TABLE pet_feedings
        ALTER COLUMN amount_unit TYPE VARCHAR(10)
        USING CASE amount_unit::text
            WHEN 'GRAMS' THEN 'g'
            WHEN 'OUNCES' THEN 'oz'
            WHEN 'KILOGRAMS' THEN 'kg'
            WHEN 'POUNDS' THEN 'lb'
            ELSE LOWER(amount_unit::text)
        END
    """)

    # Set defaults back (lowercase values)
    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit SET DEFAULT 'g'")
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit SET DEFAULT 'g'")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS foodcategory")
    op.execute("DROP TYPE IF EXISTS containerunit")


def downgrade() -> None:
    # Re-create enum types and convert back (reverse of upgrade)
    foodcategory = sa.Enum('DRY', 'WET', 'SNACK', name='foodcategory')
    containerunit = sa.Enum('GRAMS', 'OUNCES', 'KILOGRAMS', 'POUNDS', name='containerunit')

    foodcategory.create(op.get_bind(), checkfirst=True)
    containerunit.create(op.get_bind(), checkfirst=True)

    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit DROP DEFAULT")
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit DROP DEFAULT")

    op.execute("""
        ALTER TABLE pet_foods
        ALTER COLUMN category TYPE foodcategory
        USING UPPER(category)::foodcategory
    """)

    op.execute("""
        ALTER TABLE pet_foods
        ALTER COLUMN container_size_unit TYPE containerunit
        USING CASE container_size_unit
            WHEN 'g' THEN 'GRAMS'::containerunit
            WHEN 'oz' THEN 'OUNCES'::containerunit
            WHEN 'kg' THEN 'KILOGRAMS'::containerunit
            WHEN 'lb' THEN 'POUNDS'::containerunit
        END
    """)

    op.execute("""
        ALTER TABLE pet_feedings
        ALTER COLUMN amount_unit TYPE containerunit
        USING CASE amount_unit
            WHEN 'g' THEN 'GRAMS'::containerunit
            WHEN 'oz' THEN 'OUNCES'::containerunit
            WHEN 'kg' THEN 'KILOGRAMS'::containerunit
            WHEN 'lb' THEN 'POUNDS'::containerunit
        END
    """)

    op.execute("ALTER TABLE pet_foods ALTER COLUMN container_size_unit SET DEFAULT 'GRAMS'")
    op.execute("ALTER TABLE pet_feedings ALTER COLUMN amount_unit SET DEFAULT 'GRAMS'")
