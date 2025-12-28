"""SongCollaborator model for managing song access permissions."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, Enum, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, Relationship, SQLModel

from api.enums import CollaboratorRole
from api.models.utils import utc_now

if TYPE_CHECKING:
    from api.models.song import Song


class SongCollaborator(SQLModel, table=True):
    """A user's access to a song with a specific role."""

    __tablename__ = "song_collaborators"
    __table_args__ = (
        UniqueConstraint("song_id", "user_id", name="uq_song_collaborators_song_user"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    song_id: uuid.UUID = Field(foreign_key="songs.id", index=True)
    # Foreign key constraint defined in database migration
    user_id: uuid.UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), nullable=False, index=True),
    )

    role: CollaboratorRole = Field(
        default=CollaboratorRole.VIEWER,
        sa_column=Column(
            Enum(CollaboratorRole, name="collaboratorrole", create_type=False),
            nullable=False,
        ),
    )

    # Who invited this collaborator (null for owner)
    # Foreign key constraint defined in database migration
    invited_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(PGUUID(as_uuid=True), nullable=True),
    )
    invited_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )

    # When the user accepted the invitation (null if pending)
    accepted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Timestamps - must use timezone-aware columns to match utc_now()
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )

    # Relationships
    song: "Song" = Relationship(back_populates="collaborators")

    @property
    def is_owner(self) -> bool:
        """Check if this collaborator is the owner."""
        return self.role == CollaboratorRole.OWNER

    @property
    def can_edit(self) -> bool:
        """Check if this collaborator can edit the song."""
        return self.role in (CollaboratorRole.OWNER, CollaboratorRole.EDITOR)

    @property
    def is_pending(self) -> bool:
        """Check if the invitation is still pending."""
        return self.accepted_at is None and self.role != CollaboratorRole.OWNER
