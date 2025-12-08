"""create api_keys table

Revision ID: 003
Revises: 002
Create Date: 2025-12-04
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


revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "api_keys"


def upgrade() -> None:
    """Create api_keys table for programmatic API access."""

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Key identification
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),

        # Ownership
        sa.Column("user_id", sa.UUID(), nullable=False),

        # Usage tracking
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),

        # Validity
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Create indices (naming: ix_{table}_{column})
    op.create_index(f"ix_{TABLE_NAME}_key_hash", TABLE_NAME, ["key_hash"], unique=True)
    op.create_index(f"ix_{TABLE_NAME}_user_id", TABLE_NAME, ["user_id"])
    op.create_index(f"ix_{TABLE_NAME}_is_active", TABLE_NAME, ["is_active"])

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop api_keys table. Order: triggers -> indices -> table."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_is_active", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_user_id", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_key_hash", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
