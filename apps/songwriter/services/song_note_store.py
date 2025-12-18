"""Database-backed song note store using SQLModel."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.songwriter.enums import NoteType
from apps.songwriter.models import SongNote


def utc_now() -> datetime:
    """Get current UTC time (Python 3.12+ compatible)."""
    return datetime.now(timezone.utc)


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

    async def list_by_song_paginated(
        self,
        song_id: UUID,
        note_type: Optional[NoteType] = None,
        include_resolved: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SongNote], int]:
        """List notes for a song with pagination.

        Returns:
            Tuple of (notes list, total count)
        """
        from sqlalchemy import func

        # Build base query for filtering
        base_query = select(SongNote).where(SongNote.song_id == song_id)

        if note_type:
            base_query = base_query.where(SongNote.note_type == note_type)

        if not include_resolved:
            base_query = base_query.where(SongNote.is_resolved == False)  # noqa: E712

        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        query = base_query.order_by(SongNote.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        notes = list(result.scalars().all())

        return notes, total

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
        """Update a note's content or metadata.

        Allowed fields: title, content, note_type, is_resolved
        """
        note = await self.get(note_id)
        if note is None:
            return None

        # Explicit field updates
        if "title" in updates and updates["title"] is not None:
            note.title = updates["title"]
        if "content" in updates and updates["content"] is not None:
            note.content = updates["content"]
        if "note_type" in updates and updates["note_type"] is not None:
            note.note_type = updates["note_type"]
        if "is_resolved" in updates and updates["is_resolved"] is not None:
            note.is_resolved = updates["is_resolved"]

        note.updated_at = utc_now()
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
