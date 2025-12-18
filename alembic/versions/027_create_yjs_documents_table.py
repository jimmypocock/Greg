"""create yjs_documents table

Revision ID: 027
Revises: 026
Create Date: 2025-12-17

This migration creates the yjs_documents table for persisting Yjs CRDT state
for real-time collaborative editing.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from helpers import (
    add_created_at_column,
    add_updated_at_column,
    create_updated_at_trigger,
    drop_updated_at_trigger,
)


revision: str = "027"
down_revision: Union[str, Sequence[str], None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "yjs_documents"


def upgrade() -> None:
    """Create yjs_documents table for Yjs CRDT state persistence."""

    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to song
        sa.Column("song_id", sa.UUID(), nullable=False),

        # Document identifier
        sa.Column("document_name", sa.String(length=100), nullable=False, server_default="main"),

        # Yjs state (binary)
        sa.Column("state_vector", sa.LargeBinary(), nullable=True),
        sa.Column("document_state", sa.LargeBinary(), nullable=True),

        # Track last editor
        sa.Column("last_updated_by", sa.UUID(), nullable=True),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("song_id", "document_name", name="uq_yjs_documents_song_doc"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_song_id", TABLE_NAME, ["song_id"])

    # Create updated_at trigger
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop yjs_documents table."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_song_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
