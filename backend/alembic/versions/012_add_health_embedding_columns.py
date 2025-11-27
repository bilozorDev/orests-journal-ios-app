"""Add embedding columns to health tables

Revision ID: 012
Revises: 011
Create Date: 2025-11-26

Adds the missing embedding columns to pet_health_categories and pet_health_events
tables that were defined in the SQLAlchemy model but never created via migration.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('pet_health_categories',
        sa.Column('embedding', Vector(1536), nullable=True))
    op.add_column('pet_health_events',
        sa.Column('embedding', Vector(1536), nullable=True))


def downgrade() -> None:
    op.drop_column('pet_health_events', 'embedding')
    op.drop_column('pet_health_categories', 'embedding')
