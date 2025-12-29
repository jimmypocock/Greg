"""add line_type column to lines table

Revision ID: 033
Revises: 032
Create Date: 2025-12-28

This migration adds the line_type column to support canvas-based song editing.
Lines can now be: lyric, chord, section_header, or annotation.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "033"
down_revision: Union[str, Sequence[str], None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add line_type enum and column to lines table."""
    # Create the enum type (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'linetype') THEN
                CREATE TYPE linetype AS ENUM (
                    'LYRIC',
                    'CHORD',
                    'SECTION_HEADER',
                    'ANNOTATION'
                );
            END IF;
        END
        $$
    """)

    # Add the column with default value
    op.add_column(
        "lines",
        sa.Column(
            "line_type",
            sa.Enum("LYRIC", "CHORD", "SECTION_HEADER", "ANNOTATION", name="linetype", create_type=False),
            nullable=False,
            server_default="LYRIC",
        ),
    )


def downgrade() -> None:
    """Remove line_type column and enum."""
    op.drop_column("lines", "line_type")
    op.execute("DROP TYPE IF EXISTS linetype")
