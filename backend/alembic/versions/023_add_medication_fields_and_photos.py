"""Add medication fields (dosage, interval_days, is_as_needed) and photos table

Revision ID: 023
Revises: 022
Create Date: 2025-12-27

Adds new fields to support flexible medication scheduling (every N days or as-needed),
creates pet_medication_photos table, and adds medication notification preferences.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '023'
down_revision: Union[str, None] = '022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new fields to pet_medications
    op.add_column(
        'pet_medications',
        sa.Column('dosage', sa.String(255), nullable=True)
    )
    op.add_column(
        'pet_medications',
        sa.Column('interval_days', sa.Integer, nullable=True)
    )
    op.add_column(
        'pet_medications',
        sa.Column('is_as_needed', sa.Boolean, nullable=False, server_default='false')
    )

    # Set default interval_days=1 for existing scheduled medications
    op.execute("""
        UPDATE pet_medications
        SET interval_days = 1
        WHERE is_as_needed = false
    """)

    # Create pet_medication_photos table
    op.create_table(
        'pet_medication_photos',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('medication_id', UUID(as_uuid=True), sa.ForeignKey('pet_medications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('photo_url', sa.String(512), nullable=False),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
    )

    # Create index for efficient lookups by medication
    op.create_index('ix_pet_medication_photos_medication_id', 'pet_medication_photos', ['medication_id'])

    # Add medication notification preferences
    op.add_column(
        'notification_preferences',
        sa.Column('medication_created', sa.Boolean, nullable=False, server_default='true')
    )
    op.add_column(
        'notification_preferences',
        sa.Column('medication_updated', sa.Boolean, nullable=False, server_default='true')
    )
    op.add_column(
        'notification_preferences',
        sa.Column('medication_archived', sa.Boolean, nullable=False, server_default='true')
    )


def downgrade() -> None:
    # Remove medication notification preferences
    op.drop_column('notification_preferences', 'medication_archived')
    op.drop_column('notification_preferences', 'medication_updated')
    op.drop_column('notification_preferences', 'medication_created')

    # Drop the photos table
    op.drop_index('ix_pet_medication_photos_medication_id', 'pet_medication_photos')
    op.drop_table('pet_medication_photos')

    # Remove new fields from pet_medications
    op.drop_column('pet_medications', 'is_as_needed')
    op.drop_column('pet_medications', 'interval_days')
    op.drop_column('pet_medications', 'dosage')
