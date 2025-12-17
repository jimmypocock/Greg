"""add section_version_id to audio_files

Revision ID: 019
Revises: 018
Create Date: 2025-12-16

Adds section_version_id column to audio_files table.
This allows audio files to be associated with specific section versions.
NULL means song-level audio (not tied to any version).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "019"
down_revision: Union[str, Sequence[str], None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add section_version_id column to audio_files table."""

    # Add nullable column (NULL = song-level audio)
    op.add_column(
        "audio_files",
        sa.Column("section_version_id", sa.UUID(), nullable=True),
    )

    # Add foreign key with SET NULL on delete
    # (if version deleted, audio becomes song-level)
    op.create_foreign_key(
        "fk_audio_files_section_version_id",
        "audio_files",
        "section_versions",
        ["section_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add index for filtering by version
    op.create_index(
        "ix_audio_files_section_version_id",
        "audio_files",
        ["section_version_id"],
    )


def downgrade() -> None:
    """Remove section_version_id column from audio_files table."""

    op.drop_index("ix_audio_files_section_version_id", table_name="audio_files")
    op.drop_constraint("fk_audio_files_section_version_id", "audio_files", type_="foreignkey")
    op.drop_column("audio_files", "section_version_id")
