"""create section_versions table

Revision ID: 017
Revises: 016
Create Date: 2025-12-16

This migration creates the section_versions table for storing multiple
versions of song sections (workshopping different takes).
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


revision: str = "017"
down_revision: Union[str, Sequence[str], None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "section_versions"


def upgrade() -> None:
    """Create section_versions table for storing multiple versions of sections."""

    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to section
        sa.Column("section_id", sa.UUID(), nullable=False),

        # Version info
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("is_main", sa.Boolean(), nullable=False, server_default="false"),

        # Optional notes for this version
        sa.Column("notes", sa.Text(), nullable=True),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["section_id"], ["song_sections.id"], ondelete="CASCADE"),
    )

    # Create updated_at trigger
    create_updated_at_trigger(TABLE_NAME)

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_section_id", TABLE_NAME, ["section_id"])
    op.create_index(f"ix_{TABLE_NAME}_is_main", TABLE_NAME, ["is_main"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Composite index for unique version numbers per section
    op.create_index(
        f"ix_{TABLE_NAME}_section_version",
        TABLE_NAME,
        ["section_id", "version_number"],
        unique=True,
    )

    # Index for finding main version quickly
    op.create_index(
        f"ix_{TABLE_NAME}_section_main",
        TABLE_NAME,
        ["section_id", "is_main"],
    )


def downgrade() -> None:
    """Drop section_versions table."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_section_main", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_section_version", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_is_main", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_section_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
