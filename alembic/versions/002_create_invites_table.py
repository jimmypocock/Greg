"""create invites table

Revision ID: 002
Revises: 001
Create Date: 2025-12-04

Invites support three use cases:
- Referral: Users share codes to earn credits when friends sign up
- Collaboration: Invite non-users to collaborate on a specific song
- Promo: Partnership/marketing codes for bonuses
"""

from typing import Sequence, Union

from alembic import op

from helpers import create_updated_at_trigger, drop_updated_at_trigger


revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "invites"


def upgrade() -> None:
    """Create invites table for referrals, collaboration, and promos."""

    # Create enums using raw SQL
    op.execute("DO $$ BEGIN CREATE TYPE invitetype AS ENUM ('referral', 'collaboration', 'promo'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")
    op.execute("DO $$ BEGIN CREATE TYPE collaboratorrole AS ENUM ('owner', 'editor', 'viewer'); EXCEPTION WHEN duplicate_object THEN NULL; END $$")

    # Create table using raw SQL to avoid SQLAlchemy Enum auto-creation issues
    op.execute("""
        CREATE TABLE invites (
            id UUID PRIMARY KEY,
            code VARCHAR(32) NOT NULL,
            type invitetype NOT NULL DEFAULT 'referral',
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            song_id UUID,
            collaboration_role collaboratorrole,
            referrer_credits INTEGER NOT NULL DEFAULT 0,
            bonus_credits INTEGER NOT NULL DEFAULT 0,
            max_uses INTEGER,
            use_count INTEGER NOT NULL DEFAULT 0,
            expires_at TIMESTAMPTZ,
            is_active BOOLEAN NOT NULL DEFAULT true,
            email VARCHAR(255),
            promo_name VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Create indices
    op.execute(f"CREATE UNIQUE INDEX ix_{TABLE_NAME}_code ON {TABLE_NAME} (code)")
    op.execute(f"CREATE INDEX ix_{TABLE_NAME}_type ON {TABLE_NAME} (type)")
    op.execute(f"CREATE INDEX ix_{TABLE_NAME}_created_by ON {TABLE_NAME} (created_by)")
    op.execute(f"CREATE INDEX ix_{TABLE_NAME}_song_id ON {TABLE_NAME} (song_id)")
    op.execute(f"CREATE INDEX ix_{TABLE_NAME}_is_active ON {TABLE_NAME} (is_active)")
    op.execute(f"CREATE INDEX ix_{TABLE_NAME}_promo_name ON {TABLE_NAME} (promo_name)")

    # Create updated_at trigger
    create_updated_at_trigger(TABLE_NAME)


def downgrade() -> None:
    """Drop invites table."""

    drop_updated_at_trigger(TABLE_NAME)

    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_promo_name")
    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_is_active")
    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_song_id")
    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_created_by")
    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_type")
    op.execute(f"DROP INDEX IF EXISTS ix_{TABLE_NAME}_code")

    op.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")

    op.execute("DROP TYPE IF EXISTS invitetype")
    op.execute("DROP TYPE IF EXISTS collaboratorrole")
