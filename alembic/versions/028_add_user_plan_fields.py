"""Add user plan and AI credits fields.

Revision ID: 028
Revises: 027
Create Date: 2024-12-17
"""

from alembic import op
import sqlalchemy as sa


revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop enum if exists (from previous failed migration) then recreate
    op.execute("DROP TYPE IF EXISTS userplan CASCADE")
    op.execute("CREATE TYPE userplan AS ENUM ('free', 'pro', 'enterprise')")

    # Add columns using raw SQL
    op.execute("ALTER TABLE users ADD COLUMN plan userplan NOT NULL DEFAULT 'free'")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_started_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_expires_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_credits_used INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_credits_reset_at TIMESTAMPTZ")

    # Create index on stripe_customer_id for webhook lookups
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id ON users (stripe_customer_id)")


def downgrade() -> None:
    # Drop index
    op.drop_index('ix_users_stripe_customer_id', table_name='users')

    # Drop columns
    op.drop_column('users', 'ai_credits_reset_at')
    op.drop_column('users', 'ai_credits_used')
    op.drop_column('users', 'plan_expires_at')
    op.drop_column('users', 'plan_started_at')
    op.drop_column('users', 'stripe_subscription_id')
    op.drop_column('users', 'stripe_customer_id')
    op.drop_column('users', 'plan')

    # Drop enum type
    sa.Enum(name='userplan').drop(op.get_bind(), checkfirst=True)
