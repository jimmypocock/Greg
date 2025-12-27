"""Add TOTP 2FA fields to users table.

Revision ID: 030
Revises: 029
Create Date: 2024-12-20
"""

from alembic import op
import sqlalchemy as sa


revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add TOTP fields for optional 2FA
    op.add_column(
        "users",
        sa.Column("totp_secret", sa.String(32), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
