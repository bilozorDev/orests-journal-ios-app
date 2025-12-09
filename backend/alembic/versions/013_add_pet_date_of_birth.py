"""Add date_of_birth column to pets table

Revision ID: 013
Revises: 012
Create Date: 2025-12-08

Adds optional date_of_birth column to pets table for tracking pet age.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '013'
down_revision: Union[str, None] = '012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pets', sa.Column('date_of_birth', sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column('pets', 'date_of_birth')
