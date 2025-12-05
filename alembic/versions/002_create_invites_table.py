"""create invites table

Revision ID: 002
Revises: 001
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


revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "invites"


def upgrade() -> None:
    """Create invites table for user registration invitations."""

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Invite identification
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),

        # Usage tracking
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("used_by", sa.UUID(), nullable=True),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),

        # Validity
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["used_by"], ["users.id"], ondelete="SET NULL"),
    )

    # Create indices (naming: ix_{table}_{column})
    op.create_index(f"ix_{TABLE_NAME}_code", TABLE_NAME, ["code"], unique=True)
    op.create_index(f"ix_{TABLE_NAME}_created_by", TABLE_NAME, ["created_by"])
    op.create_index(f"ix_{TABLE_NAME}_is_active", TABLE_NAME, ["is_active"])
    op.create_index(f"ix_{TABLE_NAME}_expires_at", TABLE_NAME, ["expires_at"])
    op.create_index(f"ix_{TABLE_NAME}_email", TABLE_NAME, ["email"])

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop invites table. Order: triggers -> indices -> table."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_email", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_expires_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_is_active", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_by", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_code", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
