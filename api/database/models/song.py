"""
Song model.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin
from api.enums import SongStatus

if TYPE_CHECKING:
    from api.database.models.audio_file import AudioFile
    from api.database.models.song_collaborator import SongCollaborator
    from api.database.models.song_note import SongNote
    from api.database.models.song_section import SongSection


class Song(Base, TimestampMixin):
    """A complete song with structure, chords, and metadata."""

    __tablename__ = "songs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Owner
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Musical metadata
    key: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tempo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_signature: Mapped[str] = mapped_column(String(10), default="4/4", nullable=False)
    feel: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status
    status: Mapped[SongStatus] = mapped_column(
        Enum(SongStatus, name="songstatus", create_type=False),
        default=SongStatus.IDEA,
        nullable=False,
    )

    # Quick notes field
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    sections: Mapped[list["SongSection"]] = relationship(
        "SongSection",
        back_populates="song",
        cascade="all, delete-orphan",
        order_by="SongSection.order",
    )
    song_notes: Mapped[list["SongNote"]] = relationship(
        "SongNote",
        back_populates="song",
        cascade="all, delete-orphan",
        order_by="SongNote.created_at",
    )
    audio_files: Mapped[list["AudioFile"]] = relationship(
        "AudioFile",
        back_populates="song",
        cascade="all, delete-orphan",
        order_by="AudioFile.created_at",
    )
    collaborators: Mapped[list["SongCollaborator"]] = relationship(
        "SongCollaborator",
        back_populates="song",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Song {self.id} '{self.title}'>"

    def get_full_lyrics(self) -> str:
        """Get all lyrics as a single string."""
        output = []
        for section in self.sections:
            section_label = f"[{section.type.value}"
            if section.number:
                section_label += f" {section.number}"
            section_label += "]"
            output.append(section_label)
            for line in section.lines:
                output.append(line.text)
            output.append("")
        return "\n".join(output).strip()

    def get_chord_sheet(self) -> str:
        """Generate a text-based chord sheet."""
        output = []
        output.append(f"{self.title.upper()}")
        if self.key or self.tempo:
            meta = []
            if self.key:
                meta.append(f"Key: {self.key}")
            if self.tempo:
                meta.append(f"{self.tempo} BPM")
            if self.time_signature:
                meta.append(self.time_signature)
            output.append(" | ".join(meta))
        output.append("")

        for section in self.sections:
            section_label = f"[{section.type.value.title()}"
            if section.number:
                section_label += f" {section.number}"
            section_label += "]"
            output.append(section_label)

            for line in section.lines:
                if line.chords:
                    chord_line = [" "] * max(len(line.text), 1)
                    for cp in sorted(line.chords, key=lambda c: c.position):
                        pos = min(cp.position, len(chord_line) - 1)
                        for i, char in enumerate(cp.chord):
                            if pos + i < len(chord_line):
                                chord_line[pos + i] = char
                            else:
                                chord_line.append(char)
                    output.append("".join(chord_line).rstrip())
                output.append(line.text)
            output.append("")

        return "\n".join(output)

    def get_all_context(self) -> str:
        """Get all notes and context for AI consumption."""
        from api.enums import NoteType

        context_parts = []

        if self.notes:
            context_parts.append(f"Quick Notes:\n{self.notes}")

        note_groups: dict[NoteType, list[str]] = {}
        for note in self.song_notes:
            if note.note_type not in note_groups:
                note_groups[note.note_type] = []
            content = note.content
            if note.title:
                content = f"{note.title}: {content}"
            note_groups[note.note_type].append(content)

        for note_type, notes in note_groups.items():
            context_parts.append(f"\n{note_type.value}:\n" + "\n".join(f"- {n}" for n in notes))

        return "\n".join(context_parts)
