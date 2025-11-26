"""add_food_is_archived

Revision ID: 004
Revises: 003
Create Date: 2025-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pet_foods', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('ix_pet_foods_is_archived', 'pet_foods', ['is_archived'])


def downgrade() -> None:
    op.drop_index('ix_pet_foods_is_archived', table_name='pet_foods')
    op.drop_column('pet_foods', 'is_archived')
