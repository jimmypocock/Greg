"""migrate lines_data from JSONB to normalized tables

Revision ID: 014
Revises: 013
Create Date: 2025-12-16

This migration moves existing data from song_sections.lines_data JSONB column
to the new normalized lines and chord_placements tables, then drops the column.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014"
down_revision: Union[str, Sequence[str], None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate JSONB data to normalized tables and drop lines_data column."""

    # Migrate existing data from JSONB to normalized tables
    # This uses PostgreSQL's JSONB functions to extract and insert data
    op.execute("""
        INSERT INTO lines (id, section_id, "order", text, created_at, updated_at)
        SELECT
            (line_data->>'id')::uuid,
            ss.id,
            (line_data_with_index.idx - 1),
            COALESCE(line_data->>'text', ''),
            ss.created_at,
            NOW()
        FROM song_sections ss,
        LATERAL jsonb_array_elements(
            CASE
                WHEN jsonb_typeof(ss.lines_data) = 'object' THEN ss.lines_data->'lines'
                WHEN jsonb_typeof(ss.lines_data) = 'array' THEN ss.lines_data
                ELSE '[]'::jsonb
            END
        ) WITH ORDINALITY AS line_data_with_index(line_data, idx)
        WHERE ss.lines_data IS NOT NULL
          AND ss.lines_data != '[]'::jsonb
          AND ss.lines_data != '{}'::jsonb
    """)

    # Migrate chord placements
    op.execute("""
        INSERT INTO chord_placements (id, line_id, chord, position, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            (line_data->>'id')::uuid,
            chord_data->>'chord',
            (chord_data->>'position')::int,
            ss.created_at,
            NOW()
        FROM song_sections ss,
        LATERAL jsonb_array_elements(
            CASE
                WHEN jsonb_typeof(ss.lines_data) = 'object' THEN ss.lines_data->'lines'
                WHEN jsonb_typeof(ss.lines_data) = 'array' THEN ss.lines_data
                ELSE '[]'::jsonb
            END
        ) AS line_data,
        LATERAL jsonb_array_elements(
            COALESCE(line_data->'chords', '[]'::jsonb)
        ) AS chord_data
        WHERE ss.lines_data IS NOT NULL
          AND ss.lines_data != '[]'::jsonb
          AND ss.lines_data != '{}'::jsonb
          AND jsonb_array_length(COALESCE(line_data->'chords', '[]'::jsonb)) > 0
    """)

    # Drop the JSONB column
    op.drop_column("song_sections", "lines_data")


def downgrade() -> None:
    """Recreate lines_data column and migrate data back from normalized tables."""

    # Add the JSONB column back
    op.add_column(
        "song_sections",
        sa.Column(
            "lines_data",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # Migrate data back to JSONB
    # This aggregates lines and their chords back into the JSONB structure
    op.execute("""
        UPDATE song_sections ss
        SET lines_data = COALESCE(
            (
                SELECT jsonb_build_object(
                    'lines',
                    jsonb_agg(
                        jsonb_build_object(
                            'id', l.id::text,
                            'text', l.text,
                            'chords', COALESCE(
                                (
                                    SELECT jsonb_agg(
                                        jsonb_build_object(
                                            'chord', cp.chord,
                                            'position', cp.position
                                        )
                                        ORDER BY cp.position
                                    )
                                    FROM chord_placements cp
                                    WHERE cp.line_id = l.id
                                ),
                                '[]'::jsonb
                            )
                        )
                        ORDER BY l."order"
                    )
                )
                FROM lines l
                WHERE l.section_id = ss.id
            ),
            '{"lines": []}'::jsonb
        )
    """)

    # Note: We don't delete from lines/chord_placements tables in downgrade
    # because those tables will be dropped by their own migration downgrades
