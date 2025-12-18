"""add brain_dump to sectiontype enum

Revision ID: 023
Revises: 022
Create Date: 2025-12-17

This migration adds BRAIN_DUMP to the sectiontype enum for unstructured
brainstorming content.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "023"
down_revision: Union[str, Sequence[str], None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add BRAIN_DUMP value to sectiontype enum."""
    # PostgreSQL allows adding values to enums
    op.execute("ALTER TYPE sectiontype ADD VALUE IF NOT EXISTS 'BRAIN_DUMP'")


def downgrade() -> None:
    """Cannot easily remove enum values in PostgreSQL.

    To properly downgrade:
    1. Update all rows using BRAIN_DUMP to a different type
    2. Create a new enum without BRAIN_DUMP
    3. Alter the column to use the new enum
    4. Drop the old enum

    For simplicity, we leave the value in place.
    """
    pass
