"""Add user plan and AI credits fields.

Revision ID: 028_add_user_plan_fields
Revises: 027_create_yjs_documents_table
Create Date: 2024-12-17
"""

from alembic import op
import sqlalchemy as sa


revision = "028_add_user_plan_fields"
down_revision = "027_create_yjs_documents_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create UserPlan enum type
    userplan_enum = sa.Enum('free', 'pro', 'enterprise', name='userplan')
    userplan_enum.create(op.get_bind(), checkfirst=True)

    # Add plan field with default 'free'
    op.add_column(
        'users',
        sa.Column('plan', userplan_enum, nullable=False, server_default='free')
    )

    # Add Stripe fields
    op.add_column(
        'users',
        sa.Column('stripe_customer_id', sa.String(255), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True)
    )

    # Add subscription date fields
    op.add_column(
        'users',
        sa.Column('plan_started_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('plan_expires_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Add AI credits tracking
    op.add_column(
        'users',
        sa.Column('ai_credits_used', sa.Integer(), nullable=False, server_default='0')
    )
    op.add_column(
        'users',
        sa.Column('ai_credits_reset_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Create index on stripe_customer_id for webhook lookups
    op.create_index('ix_users_stripe_customer_id', 'users', ['stripe_customer_id'])


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
