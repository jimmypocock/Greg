"""create song_share_links table

Revision ID: 026
Revises: 025
Create Date: 2025-12-17

This migration creates the song_share_links table for shareable song links
that can grant access to songs.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from helpers import add_created_at_column


revision: str = "026"
down_revision: Union[str, Sequence[str], None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "song_share_links"


def upgrade() -> None:
    """Create song_share_links table."""

    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to song
        sa.Column("song_id", sa.UUID(), nullable=False),

        # Unique share token
        sa.Column("token", sa.String(length=64), nullable=False),

        # Role this link grants (reuses collaboratorrole enum from previous migration)
        sa.Column(
            "role",
            postgresql.ENUM("OWNER", "EDITOR", "VIEWER", name="collaboratorrole", create_type=False),
            nullable=False,
            server_default="VIEWER",
        ),

        # Who created this link
        sa.Column("created_by", sa.UUID(), nullable=False),

        # Expiration and usage limits
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),

        # Can be deactivated
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),

        # Timestamp
        add_created_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("token", name="uq_song_share_links_token"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_song_id", TABLE_NAME, ["song_id"])
    op.create_index(f"ix_{TABLE_NAME}_token", TABLE_NAME, ["token"])
    op.create_index(f"ix_{TABLE_NAME}_is_active", TABLE_NAME, ["is_active"])


def downgrade() -> None:
    """Drop song_share_links table."""

    op.drop_index(f"ix_{TABLE_NAME}_is_active", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_token", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_song_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
