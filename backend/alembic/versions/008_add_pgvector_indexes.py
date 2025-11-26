"""add_pgvector_indexes

Revision ID: 008
Revises: 007
Create Date: 2025-11-25

Adds HNSW (Hierarchical Navigable Small World) indexes for pgvector columns
to optimize similarity search on health category and event embeddings.

HNSW is preferred over IVFFlat because:
- Better query performance for small to medium datasets
- No training phase required
- More consistent query times
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '008'
down_revision: Union[str, None] = '007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # HNSW index for health categories embedding
    # Parameters:
    # - m=16: Number of connections per layer (default is 16, good balance)
    # - ef_construction=64: Size of dynamic candidate list during construction
    #   (higher = better quality, slower build)
    # Note: Not using CONCURRENTLY as it cannot run inside a transaction block
    # Note: Only creates index if the embedding column exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pet_health_categories' AND column_name = 'embedding'
            ) THEN
                CREATE INDEX IF NOT EXISTS ix_pet_health_categories_embedding
                ON pet_health_categories
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            END IF;
        END $$;
    """)

    # HNSW index for health events embedding
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pet_health_events' AND column_name = 'embedding'
            ) THEN
                CREATE INDEX IF NOT EXISTS ix_pet_health_events_embedding
                ON pet_health_events
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_pet_health_events_embedding")
    op.execute("DROP INDEX IF EXISTS ix_pet_health_categories_embedding")
