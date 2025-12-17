"""add audio display_name column

Revision ID: 016
Revises: 015
Create Date: 2025-12-16

Adds a display_name column to audio_files for user-editable names.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "016"
down_revision: Union[str, Sequence[str], None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add display_name column to audio_files."""
    op.add_column(
        "audio_files",
        sa.Column("display_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Remove display_name column from audio_files."""
    op.drop_column("audio_files", "display_name")
