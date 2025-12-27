"""SongShareLink model for shareable song links."""

import secrets
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Enum, text
from sqlmodel import Field, SQLModel

from api.enums import CollaboratorRole
from api.models.utils import utc_now


def generate_share_token() -> str:
    """Generate a secure, URL-safe share token."""
    return secrets.token_urlsafe(32)


class SongShareLink(SQLModel, table=True):
    """A shareable link that grants access to a song."""

    __tablename__ = "song_share_links"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    song_id: uuid.UUID = Field(foreign_key="songs.id", index=True)

    # Unique token for the share link
    token: str = Field(
        default_factory=generate_share_token,
        max_length=64,
        index=True,
        unique=True,
    )

    # What role does this link grant?
    role: CollaboratorRole = Field(
        default=CollaboratorRole.VIEWER,
        sa_column=Column(
            Enum(CollaboratorRole, name="collaboratorrole", create_type=False),
            nullable=False,
        ),
    )

    # Who created this link
    created_by: uuid.UUID = Field(foreign_key="users.id")

    # Optional expiration
    expires_at: Optional[datetime] = None

    # Usage limits
    max_uses: Optional[int] = None  # null = unlimited
    use_count: int = Field(default=0)

    # Can be deactivated without deleting
    is_active: bool = Field(default=True)

    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": text("now()")},
    )

    @property
    def is_expired(self) -> bool:
        """Check if the link has expired."""
        if self.expires_at is None:
            return False
        return utc_now() > self.expires_at

    @property
    def is_exhausted(self) -> bool:
        """Check if the link has reached its usage limit."""
        if self.max_uses is None:
            return False
        return self.use_count >= self.max_uses

    @property
    def is_valid(self) -> bool:
        """Check if the link can still be used."""
        return self.is_active and not self.is_expired and not self.is_exhausted

    def increment_use_count(self) -> None:
        """Increment the usage counter."""
        self.use_count += 1
