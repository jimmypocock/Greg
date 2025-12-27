"""Add invite relationships

Revision ID: 029
Revises: 028
Create Date: 2025-12-19

Adds:
- FK constraint from invites.song_id to songs.id
- referred_by_invite_id column on users to track which invite they used
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "029"
down_revision: Union[str, Sequence[str], None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add invite relationship constraints."""

    # Add FK from invites.song_id to songs.id
    op.create_foreign_key(
        "fk_invites_song_id",
        "invites",
        "songs",
        ["song_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # Add referred_by_invite_id to users
    op.add_column(
        "users",
        sa.Column("referred_by_invite_id", sa.UUID(), nullable=True),
    )

    # Add FK from users.referred_by_invite_id to invites.id
    op.create_foreign_key(
        "fk_users_referred_by_invite",
        "users",
        "invites",
        ["referred_by_invite_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Index for finding users by referral
    op.create_index(
        "ix_users_referred_by_invite_id",
        "users",
        ["referred_by_invite_id"],
    )


def downgrade() -> None:
    """Remove invite relationships."""

    op.drop_index("ix_users_referred_by_invite_id", table_name="users")
    op.drop_constraint("fk_users_referred_by_invite", "users", type_="foreignkey")
    op.drop_column("users", "referred_by_invite_id")
    op.drop_constraint("fk_invites_song_id", "invites", type_="foreignkey")
