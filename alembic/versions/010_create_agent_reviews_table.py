"""create agent_reviews table

Revision ID: 010
Revises: 009
Create Date: 2025-12-16

This migration creates the agent_reviews table for storing AI agent feedback
and reviews on songs. Tracks cost, performance, and review history.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from helpers import add_created_at_column


revision: str = "010"
down_revision: Union[str, Sequence[str], None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "agent_reviews"


def upgrade() -> None:
    """Create agent_reviews table for storing AI agent feedback."""

    # Create enums
    op.execute(
        "CREATE TYPE agenttype AS ENUM ('CRITIC', 'LYRICIST', 'STRUCTURE', 'MELODY')"
    )
    op.execute(
        "CREATE TYPE agenttasktype AS ENUM ("
        "'FULL_REVIEW', 'SECTION_REVIEW', 'CHECK_CLICHES', 'ANALYZE_RHYTHM', "
        "'WRITE_SECTION', 'SUGGEST_LYRICS', 'SUGGEST_CHORDS'"
        ")"
    )

    # Create table
    op.create_table(
        TABLE_NAME,
        # Primary key
        sa.Column("id", sa.UUID(), nullable=False),

        # Foreign key to song
        sa.Column("song_id", sa.UUID(), nullable=False),

        # Agent info
        sa.Column(
            "agent_type",
            postgresql.ENUM("CRITIC", "LYRICIST", "STRUCTURE", "MELODY", name="agenttype", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "task_type",
            postgresql.ENUM(
                "FULL_REVIEW", "SECTION_REVIEW", "CHECK_CLICHES", "ANALYZE_RHYTHM",
                "WRITE_SECTION", "SUGGEST_LYRICS", "SUGGEST_CHORDS",
                name="agenttasktype",
                create_type=False,
            ),
            nullable=False,
        ),

        # Review content
        sa.Column("result", sa.Text(), nullable=False),

        # Cost tracking
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0"),

        # Performance tracking
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),

        # Status
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error_message", sa.Text(), nullable=True),

        # Timestamps (no updated_at - reviews are immutable)
        add_created_at_column(),

        # Constraints
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["song_id"], ["songs.id"], ondelete="CASCADE"),
    )

    # Create indices
    op.create_index(f"ix_{TABLE_NAME}_song_id", TABLE_NAME, ["song_id"])
    op.create_index(f"ix_{TABLE_NAME}_agent_type", TABLE_NAME, ["agent_type"])
    op.create_index(f"ix_{TABLE_NAME}_task_type", TABLE_NAME, ["task_type"])
    op.create_index(f"ix_{TABLE_NAME}_created_at", TABLE_NAME, ["created_at"])
    op.create_index(f"ix_{TABLE_NAME}_success", TABLE_NAME, ["success"])

    # Composite index for song's reviews by date
    op.create_index(f"ix_{TABLE_NAME}_song_created", TABLE_NAME, ["song_id", "created_at"])


def downgrade() -> None:
    """Drop agent_reviews table. Order: indices -> table -> enums."""

    op.drop_index(f"ix_{TABLE_NAME}_song_created", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_success", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_created_at", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_task_type", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_agent_type", table_name=TABLE_NAME)
    op.drop_index(f"ix_{TABLE_NAME}_song_id", table_name=TABLE_NAME)

    op.drop_table(TABLE_NAME)

    op.execute("DROP TYPE agenttasktype")
    op.execute("DROP TYPE agenttype")
