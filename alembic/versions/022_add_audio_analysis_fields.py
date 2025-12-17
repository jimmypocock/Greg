"""Add audio analysis fields for time signature confidence, chords, and beats.

Revision ID: 022
Revises: 021
Create Date: 2024-12-16
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add confidence for time signature
    op.add_column(
        "audio_files",
        sa.Column("confidence_time_signature", sa.Float(), nullable=True),
    )

    # Add detected chords as JSON string (array of chord progressions)
    # Format: [{"start": 0.0, "end": 2.5, "chord": "C"}, ...]
    op.add_column(
        "audio_files",
        sa.Column("detected_chords", sa.Text(), nullable=True),
    )

    # Add beat positions as JSON string (array of timestamps)
    # Format: [0.5, 1.0, 1.5, 2.0, ...]
    op.add_column(
        "audio_files",
        sa.Column("beat_positions", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audio_files", "beat_positions")
    op.drop_column("audio_files", "detected_chords")
    op.drop_column("audio_files", "confidence_time_signature")
