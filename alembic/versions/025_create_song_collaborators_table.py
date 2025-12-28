"""create song_collaborators table

Revision ID: 025
Revises: 024
Create Date: 2025-12-17

This migration creates the collaboratorrole enum and song_collaborators table
for managing song access permissions and collaboration.
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


revision: str = "025"
down_revision: Union[str, Sequence[str], None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "song_collaborators"


def upgrade() -> None:
    """Create song_collaborators table (collaboratorrole enum created in migration 002)."""

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign keys
        sa.Column("song_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),

        # Role (enum created in migration 002)
        sa.Column(
            "role",
            postgresql.ENUM("OWNER", "EDITOR", "VIEWER", name="collaboratorrole", create_type=False),
            nullable=False,
        ),

        # Invitation tracking
        sa.Column("invited_by", sa.UUID(), nullable=True),
        sa.Column("invited_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("song_id", "user_id", name="uq_song_collaborators_song_user"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_song_id", TABLE_NAME, ["song_id"])
    op.create_index(f"ix_{TABLE_NAME}_user_id", TABLE_NAME, ["user_id"])
    op.create_index(f"ix_{TABLE_NAME}_role", TABLE_NAME, ["role"])

    # Create updated_at trigger
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop song_collaborators table (collaboratorrole enum dropped in migration 002)."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_role", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_user_id", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_song_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)
