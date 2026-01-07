"""Add indexes on foreign keys for CASCADE delete performance

Revision ID: 034
Revises: 033
Create Date: 2025-01-07

Adds indexes on foreign key columns that don't already have them.
These improve:
1. CASCADE delete performance (PostgreSQL scans FK tables on parent delete)
2. JOIN performance on these columns
3. Query performance for filtering by these columns
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '034'
down_revision: Union[str, None] = '033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # health_records.pet_id - querying pet's health records
    op.create_index(
        'ix_health_records_pet_id',
        'health_records',
        ['pet_id'],
        unique=False,
        if_not_exists=True
    )

    # pet_feedings.pet_id - querying pet's feedings, CASCADE delete
    op.create_index(
        'ix_pet_feedings_pet_id',
        'pet_feedings',
        ['pet_id'],
        unique=False,
        if_not_exists=True
    )

    # pet_feedings.food_id - CASCADE delete on food, joining with foods
    op.create_index(
        'ix_pet_feedings_food_id',
        'pet_feedings',
        ['food_id'],
        unique=False,
        if_not_exists=True
    )

    # pet_calorie_goals.pet_id - querying pet's calorie goals, CASCADE delete
    op.create_index(
        'ix_pet_calorie_goals_pet_id',
        'pet_calorie_goals',
        ['pet_id'],
        unique=False,
        if_not_exists=True
    )

    # pet_health_events.category_id - CASCADE delete on category
    op.create_index(
        'ix_pet_health_events_category_id',
        'pet_health_events',
        ['category_id'],
        unique=False,
        if_not_exists=True
    )

    # pet_health_event_photos.event_id - CASCADE delete on event
    op.create_index(
        'ix_pet_health_event_photos_event_id',
        'pet_health_event_photos',
        ['event_id'],
        unique=False,
        if_not_exists=True
    )

    # pet_medication_photos.medication_id - CASCADE delete on medication
    op.create_index(
        'ix_pet_medication_photos_medication_id',
        'pet_medication_photos',
        ['medication_id'],
        unique=False,
        if_not_exists=True
    )

    # medication_schedules.medication_id - CASCADE delete, schedule queries
    op.create_index(
        'ix_medication_schedules_medication_id',
        'medication_schedules',
        ['medication_id'],
        unique=False,
        if_not_exists=True
    )

    # notification_logs.medication_id - CASCADE delete on medication
    op.create_index(
        'ix_notification_logs_medication_id',
        'notification_logs',
        ['medication_id'],
        unique=False,
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index('ix_notification_logs_medication_id', table_name='notification_logs')
    op.drop_index('ix_medication_schedules_medication_id', table_name='medication_schedules')
    op.drop_index('ix_pet_medication_photos_medication_id', table_name='pet_medication_photos')
    op.drop_index('ix_pet_health_event_photos_event_id', table_name='pet_health_event_photos')
    op.drop_index('ix_pet_health_events_category_id', table_name='pet_health_events')
    op.drop_index('ix_pet_calorie_goals_pet_id', table_name='pet_calorie_goals')
    op.drop_index('ix_pet_feedings_food_id', table_name='pet_feedings')
    op.drop_index('ix_pet_feedings_pet_id', table_name='pet_feedings')
    op.drop_index('ix_health_records_pet_id', table_name='health_records')
