"""create lines table

Revision ID: 011
Revises: 010
Create Date: 2025-12-16

This migration creates the lines table for storing individual lyric lines.
Normalizes data previously stored as JSONB in song_sections.lines_data.
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


revision: str = "011"
down_revision: Union[str, Sequence[str], None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "lines"


def upgrade() -> None:
    """Create lines table for storing lyric lines."""

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to section
        sa.Column("section_id", sa.UUID(), nullable=False),

        # Line content
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),

        # Notes for this specific line
        sa.Column("notes", sa.Text(), nullable=True),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["section_id"], ["song_sections.id"], ondelete="CASCADE"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_section_id", TABLE_NAME, ["section_id"])
    op.create_index(f"ix_{TABLE_NAME}_order", TABLE_NAME, ["order"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Composite index for ordering lines within a section
    op.create_index(f"ix_{TABLE_NAME}_section_order", TABLE_NAME, ["section_id", "order"])

    # Full-text search index on lyrics
    op.execute(f"CREATE INDEX ix_{TABLE_NAME}_text_search ON {TABLE_NAME} USING gin(to_tsvector('english', text))")

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop lines table. Order: triggers -> indices -> table."""

    drop_updated_at_trigger(TABLE_NAME)

    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_text_search")
    op.drop_index(f"ix_{TABLE_NAME}_section_order", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_order", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_section_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
