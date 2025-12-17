"""add section_version_id to lines

Revision ID: 018
Revises: 017
Create Date: 2025-12-16

Adds section_version_id column to lines table (nullable for now).
Migration 020 will populate this column and 021 will make it NOT NULL.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "018"
down_revision: Union[str, Sequence[str], None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add section_version_id column to lines table."""

    # Add nullable column
    op.add_column(
        "lines",
        sa.Column("section_version_id", sa.UUID(), nullable=True),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        "fk_lines_section_version_id",
        "lines",
        "section_versions",
        ["section_version_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add index for the new column
    op.create_index("ix_lines_section_version_id", "lines", ["section_version_id"])


def downgrade() -> None:
    """Remove section_version_id column from lines table."""

    op.drop_index("ix_lines_section_version_id", table_name="lines")
    op.drop_constraint("fk_lines_section_version_id", "lines", type_="foreignkey")
    op.drop_column("lines", "section_version_id")
