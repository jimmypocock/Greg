"""Add Yjs sync tracking fields to songs.

Revision ID: 034
Revises: 033
Create Date: 2024-12-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '034'
down_revision = '033'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add yjs_synced_at - tracks when song was last synced from Yjs to SQL
    op.add_column(
        'songs',
        sa.Column('yjs_synced_at', sa.DateTime(), nullable=True)
    )

    # Add yjs_enabled - tracks if song uses Yjs for editing
    op.add_column(
        'songs',
        sa.Column('yjs_enabled', sa.Boolean(), server_default='false', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('songs', 'yjs_enabled')
    op.drop_column('songs', 'yjs_synced_at')
