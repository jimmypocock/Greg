"""Database-backed song store using SQLModel."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.database.models import ChordPlacement, Line, SectionVersion, Song, SongSection
from api.utils import utc_now

logger = logging.getLogger(__name__)


class SongDBStore:
    """Database-backed storage for songs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _song_query_options(self):
        """Get the query options to load all nested relationships."""
        return [
            selectinload(Song.sections)
            .selectinload(SongSection.versions)
            .selectinload(SectionVersion.lines)
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

    async def list_paginated(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[list[Song], int]:
        """List songs with pagination.

        Args:
            limit: Maximum number of songs to return
            offset: Number of songs to skip

        Returns:
            Tuple of (songs list, total count)
        """
        # Get total count
        count_result = await self.session.execute(select(func.count(Song.id)))
        total = count_result.scalar() or 0

        # Get paginated results
        result = await self.session.execute(
            select(Song)
            .options(*self._song_query_options())
            .order_by(Song.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        songs = list(result.scalars().all())

        return songs, total

    async def update(self, song_id: UUID, updates: dict) -> Optional[Song]:
        """Update an existing song's metadata.

        Args:
            song_id: ID of the song to update
            updates: Dict of allowed fields to update

        Allowed fields: title, raw_input, key, tempo, time_signature, feel, status, notes
        """
        song = await self.get(song_id)
        if song is None:
            return None

        # Explicit field updates with validation
        allowed_fields = {"title", "raw_input", "key", "tempo", "time_signature", "feel", "status", "notes"}
        for key, value in updates.items():
            if key not in allowed_fields:
                logger.warning(f"Attempted to update non-allowed field '{key}' on Song")
                continue
            if value is not None:
                if key == "title":
                    song.title = value
                elif key == "raw_input":
                    song.raw_input = value
                elif key == "key":
                    song.key = value
                elif key == "tempo":
                    song.tempo = value
                elif key == "time_signature":
                    song.time_signature = value
                elif key == "feel":
                    song.feel = value
                elif key == "status":
                    song.status = value
                elif key == "notes":
                    song.notes = value

        song.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(song, ["sections", "song_notes"])
        return song

    async def add_section(
        self,
        song_id: UUID,
        section: SongSection,
        after_section_id: Optional[UUID] = None,
    ) -> Optional[Song]:
        """Add a section to a song with a default version and initial empty line."""
        song = await self.get(song_id)
        if song is None:
            return None

        section.song_id = song_id

        # Determine position based on after_section_id
        if after_section_id:
            # Find the index of the section to insert after
            insert_index = None
            for i, s in enumerate(song.sections):
                if s.id == after_section_id:
                    insert_index = i + 1
                    break
            if insert_index is not None:
                section.order = insert_index
                # Shift all subsequent sections
                for s in song.sections[insert_index:]:
                    s.order += 1
            else:
                # Fallback to end if section not found
                section.order = len(song.sections)
        else:
            section.order = len(song.sections)

        # Create default version for the section
        default_version = SectionVersion(
            version_number=1,
            name="Original",
            is_main=True,
        )

        # Create an initial empty line so the user can start typing
        initial_line = Line(
            order=0,
            text="",
        )
        default_version.lines = [initial_line]
        section.versions = [default_version]

        song.sections.append(section)

        song.updated_at = utc_now()
        await self.session.commit()
        return await self.get(song_id)

    async def update_section(self, section_id: UUID, updates: dict) -> Optional[SongSection]:
        """Update a section's metadata.

        Allowed fields: type, number, order, notes
        """
        result = await self.session.execute(
            select(SongSection).where(SongSection.id == section_id)
        )
        section = result.scalar_one_or_none()
        if section is None:
            return None

        # Explicit field updates
        if "type" in updates and updates["type"] is not None:
            section.type = updates["type"]
        if "number" in updates and updates["number"] is not None:
            section.number = updates["number"]
        if "order" in updates and updates["order"] is not None:
            section.order = updates["order"]
        if "notes" in updates and updates["notes"] is not None:
            section.notes = updates["notes"]

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

    async def add_line(
        self,
        section_id: UUID,
        line: Line,
        version_id: Optional[UUID] = None,
        after_line_id: Optional[UUID] = None,
    ) -> Optional[Line]:
        """Add a line to a section's version.

        Args:
            section_id: The section ID
            line: The line to add
            version_id: Optional version ID. If not provided, adds to main version.
            after_line_id: Optional line ID to insert after. If not provided, adds at end.
        """
        # Get the section with versions
        result = await self.session.execute(
            select(SongSection)
            .options(
                selectinload(SongSection.versions)
                .selectinload(SectionVersion.lines)
            )
            .where(SongSection.id == section_id)
        )
        section = result.scalar_one_or_none()
        if section is None:
            return None

        # Find the target version
        if version_id:
            version = next((v for v in section.versions if v.id == version_id), None)
        else:
            version = section.main_version

        if version is None:
            return None

        line.section_version_id = version.id

        # Determine insertion order
        if after_line_id:
            # Find the line to insert after
            after_line = next((l for l in version.lines if l.id == after_line_id), None)
            if after_line:
                insert_order = after_line.order + 1
                # Shift subsequent lines
                for existing_line in version.lines:
                    if existing_line.order >= insert_order:
                        existing_line.order += 1
                line.order = insert_order
            else:
                # Fallback to end if after_line not found
                line.order = len(version.lines)
        else:
            # Add at end
            line.order = len(version.lines)

        self.session.add(line)
        await self.session.commit()
        await self.session.refresh(line)
        return line

    async def update_line(self, line_id: UUID, updates: dict) -> Optional[Line]:
        """Update a line's content.

        Allowed fields: text, order, notes
        """
        result = await self.session.execute(
            select(Line).where(Line.id == line_id)
        )
        line = result.scalar_one_or_none()
        if line is None:
            return None

        # Explicit field updates
        if "text" in updates and updates["text"] is not None:
            line.text = updates["text"]
        if "order" in updates and updates["order"] is not None:
            line.order = updates["order"]
        if "notes" in updates and updates["notes"] is not None:
            line.notes = updates["notes"]

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
        """Update a chord.

        Allowed fields: chord, position
        """
        result = await self.session.execute(
            select(ChordPlacement).where(ChordPlacement.id == chord_id)
        )
        chord = result.scalar_one_or_none()
        if chord is None:
            return None

        # Explicit field updates
        if "chord" in updates and updates["chord"] is not None:
            chord.chord = updates["chord"]
        if "position" in updates and updates["position"] is not None:
            chord.position = updates["position"]

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

    # =========================================================================
    # Direct lookup methods (fix N+1 queries)
    # =========================================================================

    async def get_line_with_chords(self, line_id: UUID) -> Optional[Line]:
        """Get a line by ID with its chords loaded."""
        result = await self.session.execute(
            select(Line)
            .options(selectinload(Line.chords))
            .where(Line.id == line_id)
        )
        return result.scalar_one_or_none()

    async def get_chord_by_position(
        self, line_id: UUID, position: int
    ) -> Optional[ChordPlacement]:
        """Get a chord at a specific position on a line."""
        result = await self.session.execute(
            select(ChordPlacement)
            .where(ChordPlacement.line_id == line_id)
            .where(ChordPlacement.position == position)
        )
        return result.scalar_one_or_none()

    async def verify_line_ownership(
        self, song_id: UUID, section_id: UUID, line_id: UUID
    ) -> bool:
        """Verify a line belongs to the specified song and section.

        This performs a single query instead of loading the entire song.
        """
        # Query to verify the relationship chain:
        # Line -> SectionVersion -> SongSection -> Song
        result = await self.session.execute(
            select(Line.id)
            .join(SectionVersion, Line.section_version_id == SectionVersion.id)
            .join(SongSection, SectionVersion.section_id == SongSection.id)
            .where(Line.id == line_id)
            .where(SongSection.id == section_id)
            .where(SongSection.song_id == song_id)
        )
        return result.scalar_one_or_none() is not None

    async def verify_section_ownership(self, song_id: UUID, section_id: UUID) -> bool:
        """Verify a section belongs to the specified song."""
        result = await self.session.execute(
            select(SongSection.id)
            .where(SongSection.id == section_id)
            .where(SongSection.song_id == song_id)
        )
        return result.scalar_one_or_none() is not None
