"""migrate lines to versions

Revision ID: 020
Revises: 019
Create Date: 2025-12-16

Data migration to create default section versions for existing sections
and update lines to point to them.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "020"
down_revision: Union[str, Sequence[str], None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create default versions for existing sections and migrate lines."""

    # Use raw SQL for the data migration
    # This creates a version for each section and updates lines in one go

    # Step 1: Create a default version (v1, is_main=true) for each existing section
    op.execute("""
        INSERT INTO section_versions (id, section_id, version_number, name, is_main, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            id,
            1,
            'Original',
            true,
            COALESCE(created_at, now()),
            now()
        FROM song_sections
    """)

    # Step 2: Update all lines to point to their section's new version
    op.execute("""
        UPDATE lines l
        SET section_version_id = sv.id
        FROM section_versions sv
        WHERE l.section_id = sv.section_id
          AND sv.version_number = 1
    """)


def downgrade() -> None:
    """Remove the version references and delete created versions."""

    # Step 1: Clear section_version_id from lines
    op.execute("UPDATE lines SET section_version_id = NULL")

    # Step 2: Delete all section versions created by this migration
    # (Only delete version_number=1 with name='Original' to be safe)
    op.execute("""
        DELETE FROM section_versions
        WHERE version_number = 1 AND name = 'Original'
    """)
