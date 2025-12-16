"""Database-backed song store using SQLModel."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.songwriter.models import ChordPlacement, Line, Song, SongSection


class SongDBStore:
    """Database-backed storage for songs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _song_query_options(self):
        """Get the query options to load all nested relationships."""
        return [
            selectinload(Song.sections)
            .selectinload(SongSection.lines)
            .selectinload(Line.chords),
            selectinload(Song.song_notes),
        ]

    async def create(self, song: Song) -> Song:
        """Store a new song."""
        self.session.add(song)
        await self.session.commit()
        await self.session.refresh(song, ["sections", "song_notes"])
        return song

    async def get(self, song_id: UUID) -> Optional[Song]:
        """Get a song by ID with all nested relationships loaded."""
        result = await self.session.execute(
            select(Song)
            .options(*self._song_query_options())
            .where(Song.id == song_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Song]:
        """List all songs, sorted by updated_at descending."""
        result = await self.session.execute(
            select(Song)
            .options(*self._song_query_options())
            .order_by(Song.updated_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, song_id: UUID, updates: dict) -> Optional[Song]:
        """Update an existing song's metadata.

        Args:
            song_id: ID of the song to update
            updates: Dict of fields to update
        """
        song = await self.get(song_id)
        if song is None:
            return None

        for key, value in updates.items():
            if hasattr(song, key) and value is not None:
                setattr(song, key, value)

        song.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(song, ["sections", "song_notes"])
        return song

    async def add_section(self, song_id: UUID, section: SongSection) -> Optional[Song]:
        """Add a section to a song."""
        song = await self.get(song_id)
        if song is None:
            return None

        section.song_id = song_id
        section.order = len(song.sections)
        song.sections.append(section)

        song.updated_at = datetime.utcnow()
        await self.session.commit()
        return await self.get(song_id)

    async def update_section(self, section_id: UUID, updates: dict) -> Optional[SongSection]:
        """Update a section's metadata."""
        result = await self.session.execute(
            select(SongSection).where(SongSection.id == section_id)
        )
        section = result.scalar_one_or_none()
        if section is None:
            return None

        for key, value in updates.items():
            if hasattr(section, key) and value is not None:
                setattr(section, key, value)

        await self.session.commit()
        await self.session.refresh(section)
        return section

    async def delete_section(self, section_id: UUID) -> bool:
        """Delete a section."""
        result = await self.session.execute(
            select(SongSection).where(SongSection.id == section_id)
        )
        section = result.scalar_one_or_none()
        if section is None:
            return False

        await self.session.delete(section)
        await self.session.commit()
        return True

    async def add_line(self, section_id: UUID, line: Line) -> Optional[Line]:
        """Add a line to a section."""
        result = await self.session.execute(
            select(SongSection)
            .options(selectinload(SongSection.lines))
            .where(SongSection.id == section_id)
        )
        section = result.scalar_one_or_none()
        if section is None:
            return None

        line.section_id = section_id
        line.order = len(section.lines)
        self.session.add(line)
        await self.session.commit()
        await self.session.refresh(line)
        return line

    async def update_line(self, line_id: UUID, updates: dict) -> Optional[Line]:
        """Update a line's content."""
        result = await self.session.execute(
            select(Line).where(Line.id == line_id)
        )
        line = result.scalar_one_or_none()
        if line is None:
            return None

        for key, value in updates.items():
            if hasattr(line, key) and value is not None:
                setattr(line, key, value)

        await self.session.commit()
        await self.session.refresh(line)
        return line

    async def delete_line(self, line_id: UUID) -> bool:
        """Delete a line."""
        result = await self.session.execute(
            select(Line).where(Line.id == line_id)
        )
        line = result.scalar_one_or_none()
        if line is None:
            return False

        await self.session.delete(line)
        await self.session.commit()
        return True

    async def add_chord(self, line_id: UUID, chord: ChordPlacement) -> Optional[ChordPlacement]:
        """Add a chord to a line."""
        result = await self.session.execute(
            select(Line).where(Line.id == line_id)
        )
        line = result.scalar_one_or_none()
        if line is None:
            return None

        chord.line_id = line_id
        self.session.add(chord)
        await self.session.commit()
        await self.session.refresh(chord)
        return chord

    async def update_chord(self, chord_id: UUID, updates: dict) -> Optional[ChordPlacement]:
        """Update a chord."""
        result = await self.session.execute(
            select(ChordPlacement).where(ChordPlacement.id == chord_id)
        )
        chord = result.scalar_one_or_none()
        if chord is None:
            return None

        for key, value in updates.items():
            if hasattr(chord, key) and value is not None:
                setattr(chord, key, value)

        await self.session.commit()
        await self.session.refresh(chord)
        return chord

    async def delete_chord(self, chord_id: UUID) -> bool:
        """Delete a chord."""
        result = await self.session.execute(
            select(ChordPlacement).where(ChordPlacement.id == chord_id)
        )
        chord = result.scalar_one_or_none()
        if chord is None:
            return False

        await self.session.delete(chord)
        await self.session.commit()
        return True

    async def delete(self, song_id: UUID) -> bool:
        """Delete a song. Returns True if deleted, False if not found."""
        song = await self.get(song_id)
        if song is None:
            return False

        await self.session.delete(song)
        await self.session.commit()
        return True
