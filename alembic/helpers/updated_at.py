"""
Helper for updated_at timestamp column with PostgreSQL trigger.

updated_at requires a trigger to automatically update on every UPDATE.
"""

import sqlalchemy as sa
from alembic import op


def add_updated_at_column() -> sa.Column:
    """
    Return an updated_at column with proper defaults.

    Usage in migration:
        from alembic.helpers import add_updated_at_column

        op.create_table(
            "my_table",
            sa.Column("id", sa.UUID(), nullable=False),
            add_updated_at_column(),
            ...
        )

    Note: You must also call create_updated_at_trigger() after creating the table.
    """
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def create_updated_at_trigger(table_name: str) -> None:
    """
    Create an updated_at trigger for a table.

    Call this in upgrade() after creating a table with an updated_at column.
    The trigger function is created if it doesn't exist (shared by all tables).

    Args:
        table_name: Name of the table to add the trigger to.

    Example:
        from alembic.helpers import create_updated_at_trigger

        def upgrade() -> None:
            op.create_table("my_table", ...)
            create_updated_at_trigger("my_table")
    """
    # Create the trigger function if it doesn't exist (idempotent)
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Create the trigger for this table
    op.execute(f"""
        CREATE TRIGGER update_{table_name}_updated_at
        BEFORE UPDATE ON {table_name}
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    """)


def drop_updated_at_trigger(table_name: str) -> None:
    """
    Drop the updated_at trigger for a table.

    Call this in downgrade() before dropping a table with an updated_at column.
    Note: Does NOT drop the shared trigger function (other tables may use it).

    Args:
        table_name: Name of the table to remove the trigger from.

    Example:
        from alembic.helpers import drop_updated_at_trigger

        def downgrade() -> None:
            drop_updated_at_trigger("my_table")
            op.drop_table("my_table")
    """
    op.execute(f"DROP TRIGGER IF EXISTS update_{table_name}_updated_at ON {table_name};")
