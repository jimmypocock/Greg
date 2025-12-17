"""create audio_files table

Revision ID: 015
Revises: 014
Create Date: 2025-12-16

This migration creates the audio_files table for storing uploaded audio files
and their analysis results (tempo, key, time signature).
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


revision: str = "015"
down_revision: Union[str, Sequence[str], None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "audio_files"


def upgrade() -> None:
    """Create audio_files table for storing uploaded audio files and analysis results."""

    # Create enum
    op.execute(
        "CREATE TYPE analysisstatus AS ENUM ('PENDING', 'ANALYZING', 'COMPLETED', 'FAILED')"
    )

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to song
        sa.Column("song_id", sa.UUID(), nullable=False),

        # File info
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),

        # Audio metadata
        sa.Column("duration_seconds", sa.Float(), nullable=True),

        # Analysis results
        sa.Column("detected_tempo", sa.Float(), nullable=True),
        sa.Column("detected_key", sa.String(length=20), nullable=True),
        sa.Column("detected_time_signature", sa.String(length=10), nullable=True),
        sa.Column("confidence_tempo", sa.Float(), nullable=True),
        sa.Column("confidence_key", sa.Float(), nullable=True),

        # Analysis status
        sa.Column(
            "analysis_status",
            postgresql.ENUM(
                "PENDING", "ANALYZING", "COMPLETED", "FAILED",
                name="analysisstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("analysis_error", sa.Text(), nullable=True),

        # Reference flag (if true, auto-apply to song metadata)
        sa.Column("is_reference", sa.Boolean(), nullable=False, server_default="false"),

        # Timestamps
        add_created_at_column(),
        add_updated_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
    )

    # Create updated_at trigger
    create_updated_at_trigger(TABLE_NAME)

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_song_id", TABLE_NAME, ["song_id"])
    op.create_index(f"ix_{TABLE_NAME}_analysis_status", TABLE_NAME, ["analysis_status"])
    op.create_index(f"ix_{TABLE_NAME}_is_reference", TABLE_NAME, ["is_reference"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])

    # Composite index for song's audio files by date
    op.create_index(f"ix_{TABLE_NAME}_song_created", TABLE_NAME, ["song_id", "created_at"])


def downgrade() -> None:
    """Drop audio_files table. Order: trigger -> indices -> table -> enum."""

    drop_updated_at_trigger(TABLE_NAME)

    op.drop_index(f"ix_{TABLE_NAME}_song_created", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_is_reference", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_analysis_status", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_song_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    op.execute("DROP TYPE analysisstatus")
