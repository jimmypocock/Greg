"""
Helper for created_at timestamp column.

created_at is handled by server_default, not a trigger.
This helper provides a consistent column definition.
"""

import sqlalchemy as sa


def add_created_at_column() -> sa.Column:
    """
    Return a created_at column with proper defaults.

    Usage in migration:
        from alembic.helpers import add_created_at_column

        op.create_table(
            "my_table",
            sa.Column("id", sa.UUID(), nullable=False),
            add_created_at_column(),
            ...
        )

    Note: No trigger needed - server_default handles INSERT.
    """
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )
