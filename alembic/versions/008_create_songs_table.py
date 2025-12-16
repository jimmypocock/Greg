"""create songs table

Revision ID: 008
Revises: 007
Create Date: 2025-12-15

This migration creates the songs table for storing song metadata and content.
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


revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "songs"


def upgrade() -> None:
    """Create songs table for storing song metadata."""

    # Create enum
    op.execute("CREATE TYPE songstatus AS ENUM ('IDEA', 'DRAFT', 'IN_PROGRESS', 'REVIEW', 'FINISHED')")

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Song metadata
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("key", sa.String(length=20), nullable=True),
        sa.Column("tempo", sa.Integer(), nullable=True),
        sa.Column("time_signature", sa.String(length=10), nullable=False, server_default="4/4"),
        sa.Column("feel", sa.String(length=50), nullable=True),

        # Status
        sa.Column(
            "status",
            postgresql.ENUM("IDEA", "DRAFT", "IN_PROGRESS", "REVIEW", "FINISHED", name="songstatus", create_type=False),
            nullable=False,
            server_default="IDEA",
        ),

        # Notes
        sa.Column("notes", sa.Text(), nullable=True),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_title", TABLE_NAME, ["title"])
    op.create_index(f"ix_{TABLE_NAME}_status", TABLE_NAME, ["status"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop songs table. Order: triggers -> indices -> table -> enums."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_status", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_title", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    op.execute("DROP TYPE songstatus")
