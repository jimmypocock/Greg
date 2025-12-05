"""create users table

Revision ID: 001
Revises:
Create Date: 2025-12-04

This migration serves as the convention template for all migrations.
See sections below for patterns to follow.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from helpers import (
    add_created_at_column,
    add_updated_at_column,
    create_updated_at_trigger,
    drop_updated_at_trigger,
)


revision: str = "001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "users"


def upgrade() -> None:
    """Create users table with FastAPI-Users compatible structure."""

    # Create enums (drop in downgrade AFTER table)
    op.execute("CREATE TYPE userrole AS ENUM ('USER', 'ADMIN')")

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # FastAPI-Users required fields
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),

        # Custom fields
        sa.Column(
            "role",
            postgresql.ENUM("USER", "ADMIN", name="userrole", create_type=False),
            nullable=False,
            server_default="USER",
        ),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indices (naming: ix_{table}_{column})
    op.create_index(f"ix_{TABLE_NAME}_email", TABLE_NAME, ["email"], unique=True)
    op.create_index(f"ix_{TABLE_NAME}_is_active", TABLE_NAME, ["is_active"])
    op.create_index(f"ix_{TABLE_NAME}_role", TABLE_NAME, ["role"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop users table. Order: triggers -> indices -> table -> enums."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_role", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_is_active", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_email", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    op.execute("DROP TYPE userrole")
