"""Song model (SQLModel - works for API + DB)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Enum, text
from sqlmodel import Field, Relationship, SQLModel

from apps.songwriter.enums import SongStatus
from apps.songwriter.models.utils import utc_now

if TYPE_CHECKING:
    from apps.songwriter.models.audio_file import AudioFile
    from apps.songwriter.models.song_collaborator import SongCollaborator
    from apps.songwriter.models.song_note import SongNote
    from apps.songwriter.models.song_section import SongSection


class Song(SQLModel, table=True):
    """A complete song with structure, chords, and metadata."""

    __tablename__ = "songs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=200)
    raw_input: Optional[str] = None

    # Owner - nullable initially for migration, will be NOT NULL after data migration
    owner_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)

    # Musical metadata
    key: Optional[str] = Field(default=None, max_length=20)
    tempo: Optional[int] = Field(default=None, ge=20, le=300)
    time_signature: str = Field(default="4/4", max_length=10)
    feel: Optional[str] = Field(default=None, max_length=50)

    # Status
    status: SongStatus = Field(
        default=SongStatus.IDEA,
        sa_column=Column(
            Enum(SongStatus, name="songstatus", create_type=False),
            nullable=False,
            server_default="IDEA",
        ),
    )

    # Quick notes field (for simple brain dump)
    notes: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": text("now()")},
    )

    # Relationships
    sections: list["SongSection"] = Relationship(
        back_populates="song",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "SongSection.order"},
    )
    song_notes: list["SongNote"] = Relationship(
        back_populates="song",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "SongNote.created_at"},
    )
    audio_files: list["AudioFile"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "AudioFile.created_at"},
    )
    collaborators: list["SongCollaborator"] = Relationship(
        back_populates="song",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

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
        context_parts = []

        # Add quick notes if present
        if self.notes:
            context_parts.append(f"Quick Notes:\n{self.notes}")

        # Add structured notes by type
        from apps.songwriter.enums import NoteType
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
