"""
Base classes and mixins for database models.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class TimestampMixin:
    """
    Mixin for created_at and updated_at timestamps.

    Uses server_default for created_at and a PostgreSQL trigger for updated_at.
    The trigger is created in each table's migration using helpers.
    """

    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )

    @declared_attr
    def updated_at(cls) -> Mapped[datetime]:
        return mapped_column(
            DateTime(timezone=True),
            server_default=func.now(),
            nullable=False,
        )
