"""create chord_placements table

Revision ID: 012
Revises: 011
Create Date: 2025-12-16

This migration creates the chord_placements table for storing chord positions.
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


revision: str = "012"
down_revision: Union[str, Sequence[str], None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "chord_placements"


def upgrade() -> None:
    """Create chord_placements table for storing chord positions on lines."""

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to line
        sa.Column("line_id", sa.UUID(), nullable=False),

        # Chord data
        sa.Column("chord", sa.String(length=20), nullable=False),  # e.g., "Cmaj7", "F#m"
        sa.Column("position", sa.Integer(), nullable=False),  # Character index

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["line_id"], ["lines.id"], ondelete="CASCADE"),
        sa.CheckConstraint("position >= 0", name="ck_chord_placements_position_positive"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_line_id", TABLE_NAME, ["line_id"])
    op.create_index(f"ix_{TABLE_NAME}_chord", TABLE_NAME, ["chord"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Composite index for getting all chords for a line in position order
    op.create_index(f"ix_{TABLE_NAME}_line_position", TABLE_NAME, ["line_id", "position"])

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop chord_placements table. Order: triggers -> indices -> table."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_line_position", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_chord", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_line_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
