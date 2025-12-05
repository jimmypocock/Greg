"""create refresh_tokens table

Revision ID: 007
Revises: 006
Create Date: 2025-12-04

Database-backed refresh tokens for secure session management.
Allows token revocation, session tracking, and concurrent session limits.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from helpers import add_created_at_column


revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "refresh_tokens"


def upgrade() -> None:
    """Create refresh_tokens table for secure session management."""

    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Owner
        sa.Column("user_id", sa.UUID(), nullable=False),

        # Token (stored as hash for security)
        sa.Column("token_hash", sa.String(length=255), nullable=False),

        # Expiration
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),

        # Revocation (null = active, set = revoked)
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),

        # Session metadata (device, IP, user agent, etc.)
        sa.Column("device_info", postgresql.JSONB(), nullable=True),

        # Timestamps (no updated_at - tokens are immutable, only revoked)
        add_created_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )

    # Indexes
    op.create_index(f"ix_{TABLE_NAME}_user_id", TABLE_NAME, ["user_id"])
    op.create_index(f"ix_{TABLE_NAME}_token_hash", TABLE_NAME, ["token_hash"], unique=True)
    op.create_index(f"ix_{TABLE_NAME}_expires_at", TABLE_NAME, ["expires_at"])

    # Composite index for finding active tokens
    op.create_index(
        f"ix_{TABLE_NAME}_user_active",
        TABLE_NAME,
        ["user_id", "revoked_at"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )


def downgrade() -> None:
    """Drop refresh_tokens table."""

    op.drop_index(f"ix_{TABLE_NAME}_user_active", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_expires_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_token_hash", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_user_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
