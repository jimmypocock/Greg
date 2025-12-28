"""create document_chunks table

Revision ID: 006
Revises: 005
Create Date: 2025-12-04

Note: This migration requires the pgvector extension to be available.
Supports dual embedding columns for different providers:
- embedding_local: 384 dimensions (sentence-transformers all-MiniLM-L6-v2)
- embedding_openai: 1536 dimensions (OpenAI text-embedding-3-small, ada-002)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from helpers import add_created_at_column


revision: str = "006"
down_revision: Union[str, Sequence[str], None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "document_chunks"

# Embedding dimensions by provider
LOCAL_EMBEDDING_DIM = 384   # all-MiniLM-L6-v2
OPENAI_EMBEDDING_DIM = 1536  # text-embedding-3-small, ada-002


def upgrade() -> None:
    """Create document_chunks table with pgvector for similarity search."""

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create embedding provider enum using raw SQL for proper IF NOT EXISTS
    # Use uppercase values to match Python enum names (SQLAlchemy default behavior)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'embedding_provider_enum') THEN
                CREATE TYPE embedding_provider_enum AS ENUM ('LOCAL', 'OPENAI');
            END IF;
        END$$
    """)

    # Reference the existing enum (don't auto-create)
    embedding_provider_enum = postgresql.ENUM(
        'LOCAL', 'OPENAI',
        name='embedding_provider_enum',
        create_type=False  # Don't auto-create, we did it above
    )

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Parent document
        sa.Column("document_id", sa.UUID(), nullable=False),

        # Chunk position
        sa.Column("chunk_index", sa.Integer(), nullable=False),

        # Content
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),

        # Dual embedding columns (one will be populated based on provider)
        # Using ARRAY initially, will convert to vector type after table creation
        sa.Column("embedding_local", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("embedding_openai", postgresql.ARRAY(sa.Float()), nullable=True),

        # Track which embedding provider was used
        sa.Column(
            "embedding_provider",
            embedding_provider_enum,
            nullable=False,
            server_default="LOCAL"
        ),

        # Chunk metadata (page number, section headers, etc.)
        sa.Column("chunk_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),

        # Timestamps (no updated_at - chunks are regenerated on reprocess)
        add_created_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )

    # Convert array columns to vector types for pgvector operations
    op.execute(f"""
        ALTER TABLE {TABLE_NAME}
        ALTER COLUMN embedding_local TYPE vector({LOCAL_EMBEDDING_DIM})
    """)
    op.execute(f"""
        ALTER TABLE {TABLE_NAME}
        ALTER COLUMN embedding_openai TYPE vector({OPENAI_EMBEDDING_DIM})
    """)

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_document_id", TABLE_NAME, ["document_id"])
    op.create_index(f"ix_{TABLE_NAME}_chunk_index", TABLE_NAME, ["chunk_index"])
    op.create_index(f"ix_{TABLE_NAME}_embedding_provider", TABLE_NAME, ["embedding_provider"])

    # Unique constraint: one chunk per index per document
    op.create_index(
        f"ix_{TABLE_NAME}_document_chunk_unique",
        TABLE_NAME,
        ["document_id", "chunk_index"],
        unique=True,
    )

    # HNSW indexes for fast approximate nearest neighbor search on each embedding column
    # m: max connections per layer (higher = better recall, more memory)
    # ef_construction: size of dynamic candidate list (higher = better recall, slower build)

    # Index for local embeddings (384 dim)
    op.execute(f"""
        CREATE INDEX ix_{TABLE_NAME}_embedding_local_hnsw
        ON {TABLE_NAME}
        USING hnsw (embedding_local vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # Index for OpenAI embeddings (1536 dim)
    op.execute(f"""
        CREATE INDEX ix_{TABLE_NAME}_embedding_openai_hnsw
        ON {TABLE_NAME}
        USING hnsw (embedding_openai vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Drop document_chunks table. Order: indices -> table -> enum."""

    # Drop indexes
    op.drop_index(f"ix_{TABLE_NAME}_embedding_openai_hnsw", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_embedding_local_hnsw", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_document_chunk_unique", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_embedding_provider", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_chunk_index", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_document_id", table_name=TABLE_NAME)

    # Drop table
    op.drop_table(TABLE_NAME)

    # Drop enum type
    op.execute("DROP TYPE IF EXISTS embedding_provider_enum")

    # Note: Not dropping vector extension as other tables might use it
