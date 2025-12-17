"""finalize lines schema

Revision ID: 021
Revises: 020
Create Date: 2025-12-16

Makes section_version_id NOT NULL and drops the old section_id column.
Run this after verifying migration 020 completed successfully.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "021"
down_revision: Union[str, Sequence[str], None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Finalize lines table: make section_version_id NOT NULL, drop section_id."""

    # Step 1: Make section_version_id NOT NULL
    op.alter_column(
        "lines",
        "section_version_id",
        existing_type=sa.UUID(),
        nullable=False,
    )

    # Step 2: Drop old indexes that reference section_id
    op.drop_index("ix_lines_section_order", table_name="lines")
    op.drop_index("ix_lines_section_id", table_name="lines")

    # Step 3: Drop the foreign key constraint on section_id
    op.drop_constraint("lines_section_id_fkey", "lines", type_="foreignkey")

    # Step 4: Drop the section_id column
    op.drop_column("lines", "section_id")

    # Step 5: Create new composite index for ordering within a version
    op.create_index(
        "ix_lines_version_order",
        "lines",
        ["section_version_id", "order"],
    )


def downgrade() -> None:
    """Restore section_id column and make section_version_id nullable."""

    # Step 1: Drop new composite index
    op.drop_index("ix_lines_version_order", table_name="lines")

    # Step 2: Add section_id column back
    op.add_column(
        "lines",
        sa.Column("section_id", sa.UUID(), nullable=True),
    )

    # Step 3: Restore foreign key
    op.create_foreign_key(
        "lines_section_id_fkey",
        "lines",
        "song_sections",
        ["section_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Step 4: Populate section_id from section_version
    op.execute("""
        UPDATE lines l
        SET section_id = sv.section_id
        FROM section_versions sv
        WHERE l.section_version_id = sv.id
    """)

    # Step 5: Make section_id NOT NULL
    op.alter_column(
        "lines",
        "section_id",
        existing_type=sa.UUID(),
        nullable=False,
    )

    # Step 6: Restore indexes
    op.create_index("ix_lines_section_id", "lines", ["section_id"])
    op.create_index("ix_lines_section_order", "lines", ["section_id", "order"])

    # Step 7: Make section_version_id nullable again
    op.alter_column(
        "lines",
        "section_version_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
