"""create ai_requests table

Revision ID: 004
Revises: 003
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


revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "ai_requests"


def upgrade() -> None:
    """Create ai_requests table for individual request logging."""

    # Create enums (drop in downgrade AFTER table)
    op.execute("CREATE TYPE llmprovider AS ENUM ('OLLAMA', 'ANTHROPIC', 'OPENAI', 'GOOGLE')")
    op.execute("CREATE TYPE requesttype AS ENUM ('CHAT', 'SEARCH')")

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Request context
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "request_type",
            postgresql.ENUM("CHAT", "SEARCH", name="requesttype", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "provider",
            postgresql.ENUM("OLLAMA", "ANTHROPIC", "OPENAI", "GOOGLE", name="llmprovider", create_type=False),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=100), nullable=False),

        # Token counts
        sa.Column("input_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cached_tokens", sa.BigInteger(), nullable=False, server_default="0"),

        # Cost breakdown (precision: 6 decimal places for fractional cents)
        sa.Column("input_cost_usd", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),
        sa.Column("output_cost_usd", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),

        # Performance
        sa.Column("latency_ms", sa.Integer(), nullable=True),

        # Status
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error_message", sa.Text(), nullable=True),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Create indices (naming: ix_{table}_{column})
    op.create_index(f"ix_{TABLE_NAME}_user_id", TABLE_NAME, ["user_id"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])
    op.create_index(f"ix_{TABLE_NAME}_provider", TABLE_NAME, ["provider"])
    op.create_index(f"ix_{TABLE_NAME}_model", TABLE_NAME, ["model"])
    op.create_index(f"ix_{TABLE_NAME}_success", TABLE_NAME, ["success"])
    op.create_index(f"ix_{TABLE_NAME}_request_type", TABLE_NAME, ["request_type"])

    # Composite indices for common queries
    op.create_index(f"ix_{TABLE_NAME}_user_created", TABLE_NAME, ["user_id", "created_at"])
    op.create_index(f"ix_{TABLE_NAME}_provider_created", TABLE_NAME, ["provider", "created_at"])

    # Create triggers
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop ai_requests table. Order: triggers -> indices -> table -> enums."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_provider_created", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_user_created", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_request_type", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_success", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_model", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_provider", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_user_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    # Drop enums
    op.execute("DROP TYPE requesttype")
    op.execute("DROP TYPE llmprovider")
