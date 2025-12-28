"""create song_notes table

Revision ID: 013
Revises: 012
Create Date: 2025-12-16

This migration creates the song_notes table for storing structured brain dump
notes, ideas, inspirations, and context that AI agents can use for suggestions.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from helpers import (
    add_created_at_column,
    add_updated_at_column,
    create_updated_at_trigger,
    drop_updated_at_trigger,
)


revision: str = "013"
down_revision: Union[str, Sequence[str], None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "song_notes"


def upgrade() -> None:
    """Create song_notes table for storing structured notes and ideas."""

    # Create enum for note types
    op.execute(
        "CREATE TYPE notetype AS ENUM ("
        "'IDEA', 'INSPIRATION', 'REFERENCE', 'CONTEXT', 'TODO', 'FEEDBACK', 'OTHER', 'SONG_SHAPE'"
        ")"
    )

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to song (required)
        sa.Column("song_id", sa.UUID(), nullable=False),

        # Optional link to specific section
        sa.Column("section_id", sa.UUID(), nullable=True),

        # Note type for categorization
        sa.Column(
            "note_type",
            postgresql.ENUM(
                "IDEA", "INSPIRATION", "REFERENCE", "CONTEXT", "TODO", "FEEDBACK", "OTHER", "SONG_SHAPE",
                name="notetype",
                create_type=False,
            ),
            nullable=False,
            server_default="IDEA",
        ),

        # The actual content
        sa.Column("content", sa.Text(), nullable=False),

        # Optional title/summary for quick scanning
        sa.Column("title", sa.String(length=200), nullable=True),

        # Is this note resolved/completed? (useful for TODOs)
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default="false"),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["song_sections.id"], ondelete="CASCADE"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_song_id", TABLE_NAME, ["song_id"])
    op.create_index(f"ix_{TABLE_NAME}_section_id", TABLE_NAME, ["section_id"])
    op.create_index(f"ix_{TABLE_NAME}_note_type", TABLE_NAME, ["note_type"])
    op.create_index(f"ix_{TABLE_NAME}_is_resolved", TABLE_NAME, ["is_resolved"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Composite index for getting all notes for a song by type
    op.create_index(f"ix_{TABLE_NAME}_song_type", TABLE_NAME, ["song_id", "note_type"])

    # Composite index for unresolved TODOs
    op.create_index(
        f"ix_{TABLE_NAME}_song_unresolved",
        TABLE_NAME,
        ["song_id", "is_resolved"],
        postgresql_where=sa.text("is_resolved = false"),
    )

    # Full-text search on content
    op.execute(f"CREATE INDEX ix_{TABLE_NAME}_content_search ON {TABLE_NAME} USING gin(to_tsvector('english', content))")

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop song_notes table. Order: triggers -> indices -> table -> enums."""

    drop_updated_at_trigger(TABLE_NAME)

    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_content_search")
    op.drop_index(f"ix_{TABLE_NAME}_song_unresolved", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_song_type", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_is_resolved", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_note_type", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_section_id", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_song_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    op.execute("DROP TYPE notetype")
