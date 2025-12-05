"""create documents table

Revision ID: 005
Revises: 004
Create Date: 2025-12-04
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


revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "documents"


def upgrade() -> None:
    """Create documents table for storing document metadata."""

    # Create enum
    op.execute("CREATE TYPE documentstatus AS ENUM ('PENDING', 'PROCESSING', 'READY', 'FAILED')")

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Ownership
        sa.Column("user_id", sa.UUID(), nullable=False),

        # File info
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),

        # Processing status
        sa.Column(
            "status",
            postgresql.ENUM("PENDING", "PROCESSING", "READY", "FAILED", name="documentstatus", create_type=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),

        # Processing results
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),

        # Flexible metadata (page count, author, etc.)
        sa.Column("extra_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_user_id", TABLE_NAME, ["user_id"])
    op.create_index(f"ix_{TABLE_NAME}_status", TABLE_NAME, ["status"])
    op.create_index(f"ix_{TABLE_NAME}_file_type", TABLE_NAME, ["file_type"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Composite index for user's documents by status
    op.create_index(f"ix_{TABLE_NAME}_user_status", TABLE_NAME, ["user_id", "status"])

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop documents table. Order: triggers -> indices -> table -> enums."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_user_status", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_file_type", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_status", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_user_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    op.execute("DROP TYPE documentstatus")
