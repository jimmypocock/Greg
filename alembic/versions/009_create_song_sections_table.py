"""create song_sections table

Revision ID: 009
Revises: 008
Create Date: 2025-12-15

This migration creates the song_sections table for storing individual sections
of a song (verses, choruses, bridges, etc.) with their lyrics and metadata.
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


revision: str = "009"
down_revision: Union[str, Sequence[str], None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "song_sections"


def upgrade() -> None:
    """Create song_sections table for storing song section content."""

    # Create enum
    op.execute(
        "CREATE TYPE sectiontype AS ENUM ("
        "'INTRO', 'VERSE', 'PRE_CHORUS', 'CHORUS', 'POST_CHORUS', "
        "'BRIDGE', 'OUTRO', 'INSTRUMENTAL', 'SOLO', 'BREAKDOWN', 'BRAIN_DUMP', 'OTHER'"
        ")"
    )

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to song
        sa.Column("song_id", sa.UUID(), nullable=False),

        # Section metadata
        sa.Column(
            "type",
            postgresql.ENUM(
                "INTRO", "VERSE", "PRE_CHORUS", "CHORUS", "POST_CHORUS",
                "BRIDGE", "OUTRO", "INSTRUMENTAL", "SOLO", "BREAKDOWN", "BRAIN_DUMP", "OTHER",
                name="sectiontype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=True),  # e.g., Verse 1, Verse 2
        sa.Column("order", sa.Integer(), nullable=False),  # Position in song

        # Content
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("lines_data", postgresql.JSONB(), nullable=False, server_default="[]"),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_song_id", TABLE_NAME, ["song_id"])
    op.create_index(f"ix_{TABLE_NAME}_type", TABLE_NAME, ["type"])
    op.create_index(f"ix_{TABLE_NAME}_order", TABLE_NAME, ["order"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Composite index for ordering sections within a song
    op.create_index(f"ix_{TABLE_NAME}_song_order", TABLE_NAME, ["song_id", "order"])

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop song_sections table. Order: triggers -> indices -> table -> enums."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_song_order", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_order", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_type", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_song_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    op.execute("DROP TYPE sectiontype")
