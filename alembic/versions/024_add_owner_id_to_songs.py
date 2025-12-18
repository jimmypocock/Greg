"""add owner_id to songs table

Revision ID: 024
Revises: 023
Create Date: 2025-12-17

This migration adds owner_id column to songs table for tracking song ownership.
Initially nullable for migration, will be made NOT NULL after data migration.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "024"
down_revision: Union[str, Sequence[str], None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "songs"


def upgrade() -> None:
    """Add owner_id column to songs table."""
    op.add_column(
        TABLE_NAME,
        sa.Column("owner_id", sa.UUID(), nullable=True),
    )

    # Add foreign key constraint
    op.create_foreign_key(
        f"fk_{TABLE_NAME}_owner_id",
        TABLE_NAME,
        "users",
        ["owner_id"],
        ["id"],
        ondelete="SET NULL",  # Don't cascade delete songs when user is deleted
    )

    # Add index for efficient lookups
    op.create_index(f"ix_{TABLE_NAME}_owner_id", TABLE_NAME, ["owner_id"])


def downgrade() -> None:
    """Remove owner_id column from songs table."""
    op.drop_index(f"ix_{TABLE_NAME}_owner_id", table_name=TABLE_NAME)
    op.drop_constraint(f"fk_{TABLE_NAME}_owner_id", TABLE_NAME, type_="foreignkey")
    op.drop_column(TABLE_NAME, "owner_id")
