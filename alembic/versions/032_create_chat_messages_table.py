"""create chat_messages table

Revision ID: 032
Revises: 031
Create Date: 2025-12-27

This migration creates the chat_messages table for persisting
conversation history between users and AI agents for each song.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from helpers import add_created_at_column


revision: str = "032"
down_revision: Union[str, Sequence[str], None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "chat_messages"


def upgrade() -> None:
    """Create chat_messages table for conversation persistence."""

    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to song
        sa.Column("song_id", sa.UUID(), nullable=False),

        # Message role: 'user' or 'assistant'
        sa.Column("role", sa.String(length=20), nullable=False),

        # Message content
        sa.Column("content", sa.Text(), nullable=False),

        # Optional metadata for assistant messages
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_cost_usd", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),

        # Timestamp
        add_created_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_song_id", TABLE_NAME, ["song_id"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Composite index for getting conversation in order
    op.create_index(f"ix_{TABLE_NAME}_song_created", TABLE_NAME, ["song_id", "created_at"])


def downgrade() -> None:
    """Drop chat_messages table."""
    op.drop_index(f"ix_{TABLE_NAME}_song_created", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_song_id", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
