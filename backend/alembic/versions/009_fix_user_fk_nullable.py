"""fix_user_fk_nullable

Revision ID: 009
Revises: 008
Create Date: 2025-11-26

Makes created_by, fed_by, and given_by columns nullable to allow
SET NULL on delete to work properly when a user is deleted.

The original migration (007) created these columns with NOT NULL constraint
but with ondelete='SET NULL', which is a contradiction. This migration
fixes that by making the columns nullable.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '009'
down_revision: Union[str, None] = '008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make all user reference columns nullable to allow SET NULL on delete

    # pets.created_by
    op.alter_column('pets', 'created_by', nullable=True)

    # pet_foods.created_by
    op.alter_column('pet_foods', 'created_by', nullable=True)

    # pet_feedings.fed_by
    op.alter_column('pet_feedings', 'fed_by', nullable=True)

    # pet_calorie_goals.created_by
    op.alter_column('pet_calorie_goals', 'created_by', nullable=True)

    # pet_medications.created_by
    op.alter_column('pet_medications', 'created_by', nullable=True)

    # pet_medication_doses.given_by
    op.alter_column('pet_medication_doses', 'given_by', nullable=True)

    # pet_health_categories.created_by
    op.alter_column('pet_health_categories', 'created_by', nullable=True)

    # pet_health_events.created_by
    op.alter_column('pet_health_events', 'created_by', nullable=True)


def downgrade() -> None:
    # Restore NOT NULL constraints
    # Note: This will fail if any NULL values exist in the columns

    op.alter_column('pet_health_events', 'created_by', nullable=False)
    op.alter_column('pet_health_categories', 'created_by', nullable=False)
    op.alter_column('pet_medication_doses', 'given_by', nullable=False)
    op.alter_column('pet_medications', 'created_by', nullable=False)
    op.alter_column('pet_calorie_goals', 'created_by', nullable=False)
    op.alter_column('pet_feedings', 'fed_by', nullable=False)
    op.alter_column('pet_foods', 'created_by', nullable=False)
    op.alter_column('pets', 'created_by', nullable=False)
