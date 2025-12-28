"""add shape note types to notetype enum

Revision ID: 031
Revises: 030
Create Date: 2025-12-27

This migration adds new NoteType enum values for song shape exploration:
- THEME: The song's core theme/concept
- KEY_IMAGE: Key images, phrases, or metaphors
- EMOTIONAL_ARC: The emotional journey
- FRAGMENT: User's raw lyric fragments
"""

from typing import Sequence, Union

from alembic import op


revision: str = "031"
down_revision: Union[str, Sequence[str], None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add new note type enum values for song shape exploration."""
    # PostgreSQL allows adding values to an enum with ALTER TYPE
    op.execute("ALTER TYPE notetype ADD VALUE IF NOT EXISTS 'THEME'")
    op.execute("ALTER TYPE notetype ADD VALUE IF NOT EXISTS 'KEY_IMAGE'")
    op.execute("ALTER TYPE notetype ADD VALUE IF NOT EXISTS 'EMOTIONAL_ARC'")
    op.execute("ALTER TYPE notetype ADD VALUE IF NOT EXISTS 'FRAGMENT'")


def downgrade() -> None:
    """Cannot easily remove enum values in PostgreSQL.

    To properly downgrade, you would need to:
    1. Create a new enum without these values
    2. Update all rows using these values to a different type
    3. Drop the old enum and rename the new one

    For now, we'll leave the enum values in place.
    """
    pass
