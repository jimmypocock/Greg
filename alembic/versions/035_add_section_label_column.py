"""Add label column to song_sections for custom part names.

Revision ID: 035
Revises: 034
Create Date: 2024-12-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add label column - nullable, user can set custom label
    op.add_column(
        "song_sections",
        sa.Column("label", sa.String(200), nullable=True),
    )

    # Populate existing rows with derived label from type + number
    # This makes the migration non-destructive
    op.execute("""
        UPDATE song_sections
        SET label = CASE
            WHEN number IS NOT NULL THEN
                INITCAP(REPLACE(type::text, '_', ' ')) || ' ' || number::text
            ELSE
                INITCAP(REPLACE(type::text, '_', ' '))
        END
        WHERE label IS NULL
    """)


def downgrade() -> None:
    op.drop_column("song_sections", "label")
