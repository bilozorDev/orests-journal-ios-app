"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create pets table
    op.create_table(
        'pets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', sa.String(255), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('kind', sa.String(100), nullable=False),
        sa.Column('photo_url', sa.String(500), nullable=True),
        sa.Column('current_weight', sa.Float, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create health_records table
    op.create_table(
        'health_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('age_years', sa.Float, nullable=True),
        sa.Column('weight_pounds', sa.Float, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('recorded_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create pet_foods table
    op.create_table(
        'pet_foods',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', sa.String(255), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('calories_per_kg', sa.Float, nullable=False),
        sa.Column('container_size', sa.Float, nullable=False),
        sa.Column('container_size_unit', sa.String(10), nullable=False, server_default='g'),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create pet_feedings table
    op.create_table(
        'pet_feedings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('food_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pet_foods.id', ondelete='CASCADE'), nullable=False),
        sa.Column('fed_by', sa.String(255), nullable=False),
        sa.Column('fed_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('amount', sa.Float, nullable=False),
        sa.Column('amount_unit', sa.String(10), nullable=False, server_default='g'),
        sa.Column('calories', sa.Float, nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create pet_calorie_goals table
    op.create_table(
        'pet_calorie_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('daily_calories', sa.Float, nullable=False),
        sa.Column('effective_from', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('effective_until', sa.DateTime, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create pet_medications table
    op.create_table(
        'pet_medications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('medication_type', sa.String(50), nullable=False),
        sa.Column('start_date', sa.DateTime, nullable=False),
        sa.Column('end_date', sa.DateTime, nullable=True),
        sa.Column('times_per_day', sa.Integer, nullable=False, server_default='1'),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create pet_medication_doses table
    op.create_table(
        'pet_medication_doses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('medication_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pet_medications.id', ondelete='CASCADE'), nullable=False),
        sa.Column('given_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('given_by', sa.String(255), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create pet_health_categories table
    op.create_table(
        'pet_health_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('name_normalized', sa.String(255), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create pet_health_events table
    op.create_table(
        'pet_health_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('pet_health_categories.id', ondelete='CASCADE'), nullable=False),
        sa.Column('occurred_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('ix_pet_feedings_pet_fed_at', 'pet_feedings', ['pet_id', 'fed_at'])
    op.create_index('ix_pet_medication_doses_medication_given_at', 'pet_medication_doses', ['medication_id', 'given_at'])
    op.create_index('ix_pet_health_events_category_occurred', 'pet_health_events', ['category_id', 'occurred_at'])


def downgrade() -> None:
    op.drop_table('pet_health_events')
    op.drop_table('pet_health_categories')
    op.drop_table('pet_medication_doses')
    op.drop_table('pet_medications')
    op.drop_table('pet_calorie_goals')
    op.drop_table('pet_feedings')
    op.drop_table('pet_foods')
    op.drop_table('health_records')
    op.drop_table('pets')
    op.execute('DROP EXTENSION IF EXISTS vector')
