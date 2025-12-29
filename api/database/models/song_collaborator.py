"""
SongCollaborator model.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin
from api.enums import CollaboratorRole

if TYPE_CHECKING:
    from api.database.models.song import Song


class SongCollaborator(Base, TimestampMixin):
    """A user's access to a song with a specific role."""

    __tablename__ = "song_collaborators"
    __table_args__ = (
        UniqueConstraint("song_id", "user_id", name="uq_song_collaborators_song_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    role: Mapped[CollaboratorRole] = mapped_column(
        Enum(CollaboratorRole, name="collaboratorrole", create_type=False),
        default=CollaboratorRole.VIEWER,
        nullable=False,
    )

    # Who invited this collaborator (null for owner)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    invited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # When the user accepted the invitation (null if pending)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        status = "pending" if self.is_pending else "active"
        return f"<SongCollaborator {self.role.value} ({status})>"

    # Relationships
    song: Mapped["Song"] = relationship("Song", back_populates="collaborators")

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
