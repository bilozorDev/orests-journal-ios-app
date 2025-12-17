"""Add support for multiple photos per health event

Revision ID: 017
Revises: 016
Create Date: 2025-12-15

Creates pet_health_event_photos table and migrates existing photo_url data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '017'
down_revision: Union[str, None] = '016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the new photos table
    op.create_table(
        'pet_health_event_photos',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('pet_health_events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('photo_url', sa.String(512), nullable=False),
        sa.Column('sort_order', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('now()')),
    )

    # Create index for efficient lookups by event
    op.create_index('ix_pet_health_event_photos_event_id', 'pet_health_event_photos', ['event_id'])

    # Migrate existing photo_url data to the new table
    op.execute("""
        INSERT INTO pet_health_event_photos (event_id, photo_url, sort_order, created_at)
        SELECT id, photo_url, 0, created_at
        FROM pet_health_events
        WHERE photo_url IS NOT NULL AND photo_url != ''
    """)

    # Drop the old column
    op.drop_column('pet_health_events', 'photo_url')


def downgrade() -> None:
    # Re-add the photo_url column
    op.add_column(
        'pet_health_events',
        sa.Column('photo_url', sa.String(512), nullable=True)
    )

    # Migrate the first photo back (only one can fit in single column)
    op.execute("""
        UPDATE pet_health_events e
        SET photo_url = (
            SELECT photo_url
            FROM pet_health_event_photos p
            WHERE p.event_id = e.id
            ORDER BY p.sort_order, p.created_at
            LIMIT 1
        )
    """)

    # Drop the index and table
    op.drop_index('ix_pet_health_event_photos_event_id', 'pet_health_event_photos')
    op.drop_table('pet_health_event_photos')
