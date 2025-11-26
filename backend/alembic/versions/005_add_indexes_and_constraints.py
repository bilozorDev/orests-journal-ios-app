"""add_indexes_and_constraints

Revision ID: 005
Revises: cb2cb23d8190
Create Date: 2025-11-25

Adds performance indexes and CHECK constraints for data integrity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================
    # PERFORMANCE INDEXES
    # ============================================

    # Critical: Index for authorization checks (user -> families lookup)
    op.create_index(
        'ix_family_members_user_id',
        'family_members',
        ['user_id'],
        unique=False
    )

    # Date-range queries for feedings
    op.create_index(
        'ix_pet_feedings_fed_at',
        'pet_feedings',
        ['fed_at'],
        unique=False
    )

    # Date-range queries for medication doses
    op.create_index(
        'ix_pet_medication_doses_given_at',
        'pet_medication_doses',
        ['given_at'],
        unique=False
    )

    # Calorie goal lookups (pet + date range)
    op.create_index(
        'ix_pet_calorie_goals_pet_date',
        'pet_calorie_goals',
        ['pet_id', sa.text('effective_from DESC'), 'effective_until'],
        unique=False
    )

    # Health records timeline
    op.create_index(
        'ix_health_records_pet_recorded',
        'health_records',
        ['pet_id', sa.text('recorded_at DESC')],
        unique=False
    )

    # ============================================
    # CHECK CONSTRAINTS for data integrity
    # ============================================

    # Family member role must be 'admin' or 'member'
    op.create_check_constraint(
        'chk_family_member_role',
        'family_members',
        "role IN ('admin', 'member')"
    )

    # Food category must be valid
    op.create_check_constraint(
        'chk_food_category',
        'pet_foods',
        "category IN ('dry', 'wet', 'snack')"
    )

    # Medication type must be valid
    op.create_check_constraint(
        'chk_medication_type',
        'pet_medications',
        "medication_type IN ('drops', 'pill', 'inhaler', 'shot', 'liquid', 'tablet', 'capsule', 'topical')"
    )


def downgrade() -> None:
    # Drop CHECK constraints
    op.drop_constraint('chk_medication_type', 'pet_medications', type_='check')
    op.drop_constraint('chk_food_category', 'pet_foods', type_='check')
    op.drop_constraint('chk_family_member_role', 'family_members', type_='check')

    # Drop indexes
    op.drop_index('ix_health_records_pet_recorded', table_name='health_records')
    op.drop_index('ix_pet_calorie_goals_pet_date', table_name='pet_calorie_goals')
    op.drop_index('ix_pet_medication_doses_given_at', table_name='pet_medication_doses')
    op.drop_index('ix_pet_feedings_fed_at', table_name='pet_feedings')
    op.drop_index('ix_family_members_user_id', table_name='family_members')
