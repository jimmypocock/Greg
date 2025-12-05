"""create document_chunks table

Revision ID: 006
Revises: 005
Create Date: 2025-12-04

Note: This migration requires the pgvector extension to be available.
The embedding dimension (1536) matches OpenAI's text-embedding-ada-002
and text-embedding-3-small models. Adjust if using different models.
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

# Embedding dimension - adjust based on your embedding model
# 1536: OpenAI ada-002, text-embedding-3-small
# 3072: OpenAI text-embedding-3-large
# 768: Many open source models (sentence-transformers)
EMBEDDING_DIMENSION = 1536


def upgrade() -> None:
    """Create document_chunks table with pgvector for similarity search."""

    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

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

        # Vector embedding (using pgvector)
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),

        # Chunk metadata (page number, section headers, etc.)
        sa.Column("chunk_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),

        # Timestamps (no updated_at - chunks are regenerated on reprocess)
        add_created_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )

    # Convert the array column to vector type for pgvector operations
    op.execute(f"ALTER TABLE {TABLE_NAME} ALTER COLUMN embedding TYPE vector({EMBEDDING_DIMENSION})")

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_document_id", TABLE_NAME, ["document_id"])
    op.create_index(f"ix_{TABLE_NAME}_chunk_index", TABLE_NAME, ["chunk_index"])

    # Unique constraint: one chunk per index per document
    op.create_index(
        f"ix_{TABLE_NAME}_document_chunk_unique",
        TABLE_NAME,
        ["document_id", "chunk_index"],
        unique=True,
    )

    # HNSW index for fast approximate nearest neighbor search
    # m: max connections per layer (higher = better recall, more memory)
    # ef_construction: size of dynamic candidate list (higher = better recall, slower build)
    op.execute(f"""
        CREATE INDEX ix_{TABLE_NAME}_embedding_hnsw
        ON {TABLE_NAME}
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    """Drop document_chunks table. Order: indices -> table -> extension."""

    op.drop_index(f"ix_{TABLE_NAME}_embedding_hnsw", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_document_chunk_unique", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_chunk_index", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_document_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    # Note: Not dropping vector extension as other tables might use it
