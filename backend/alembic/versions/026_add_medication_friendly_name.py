"""Add friendly_name to medications

Revision ID: 026
Revises: 025
Create Date: 2024-12-30
"""
from alembic import op
import sqlalchemy as sa


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pet_medications",
        sa.Column("friendly_name", sa.String(100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("pet_medications", "friendly_name")
