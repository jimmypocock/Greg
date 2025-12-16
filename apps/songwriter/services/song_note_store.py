"""Database-backed song note store using SQLModel."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.songwriter.enums import NoteType
from apps.songwriter.models import SongNote


class SongNoteStore:
    """Database-backed storage for song notes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, note: SongNote) -> SongNote:
        """Create a new song note."""
        self.session.add(note)
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def get(self, note_id: UUID) -> Optional[SongNote]:
        """Get a note by ID."""
        result = await self.session.execute(
            select(SongNote).where(SongNote.id == note_id)
        )
        return result.scalar_one_or_none()

    async def list_by_song(
        self,
        song_id: UUID,
        note_type: Optional[NoteType] = None,
        include_resolved: bool = True,
    ) -> list[SongNote]:
        """List all notes for a song, optionally filtered by type."""
        query = select(SongNote).where(SongNote.song_id == song_id)

        if note_type:
            query = query.where(SongNote.note_type == note_type)

        if not include_resolved:
            query = query.where(SongNote.is_resolved == False)  # noqa: E712

        query = query.order_by(SongNote.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_by_section(
        self,
        section_id: UUID,
        note_type: Optional[NoteType] = None,
    ) -> list[SongNote]:
        """List all notes for a specific section."""
        query = select(SongNote).where(SongNote.section_id == section_id)

        if note_type:
            query = query.where(SongNote.note_type == note_type)

        query = query.order_by(SongNote.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, note_id: UUID, updates: dict) -> Optional[SongNote]:
        """Update a note's content or metadata."""
        note = await self.get(note_id)
        if note is None:
            return None

        for key, value in updates.items():
            if hasattr(note, key) and value is not None:
                setattr(note, key, value)

        note.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(note)
        return note

    async def resolve(self, note_id: UUID) -> Optional[SongNote]:
        """Mark a note as resolved (useful for TODOs)."""
        return await self.update(note_id, {"is_resolved": True})

    async def unresolve(self, note_id: UUID) -> Optional[SongNote]:
        """Mark a note as unresolved."""
        return await self.update(note_id, {"is_resolved": False})

    async def delete(self, note_id: UUID) -> bool:
        """Delete a note. Returns True if deleted, False if not found."""
        note = await self.get(note_id)
        if note is None:
            return False

        await self.session.delete(note)
        await self.session.commit()
        return True

    async def get_unresolved_todos(self, song_id: UUID) -> list[SongNote]:
        """Get all unresolved TODO notes for a song."""
        return await self.list_by_song(
            song_id,
            note_type=NoteType.TODO,
            include_resolved=False,
        )

    async def get_context_for_ai(self, song_id: UUID) -> str:
        """Get all notes formatted for AI consumption."""
        notes = await self.list_by_song(song_id)

        if not notes:
            return ""

        # Group by type
        note_groups: dict[NoteType, list[str]] = {}
        for note in notes:
            if note.note_type not in note_groups:
                note_groups[note.note_type] = []
            content = note.content
            if note.title:
                content = f"{note.title}: {content}"
            if note.is_resolved:
                content = f"[RESOLVED] {content}"
            note_groups[note.note_type].append(content)

        # Format output
        output = []
        for note_type, contents in note_groups.items():
            output.append(f"{note_type.value}:")
            for content in contents:
                output.append(f"  - {content}")

        return "\n".join(output)
