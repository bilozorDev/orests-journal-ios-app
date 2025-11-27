"""add_medication_is_archived

Revision ID: 011
Revises: 010
Create Date: 2025-11-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pet_medications', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'))
    op.create_index('ix_pet_medications_is_archived', 'pet_medications', ['is_archived'])


def downgrade() -> None:
    op.drop_index('ix_pet_medications_is_archived', table_name='pet_medications')
    op.drop_column('pet_medications', 'is_archived')
