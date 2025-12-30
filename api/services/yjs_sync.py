"""
Sync service between Yjs documents and SQL database.

Two-way sync:
  - SQL → Yjs: When first loading a song in canvas mode
  - Yjs → SQL: Periodically + on disconnect (for AI/queries/versions)
"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pycrdt import Doc, Text

from api.database.models import (
    Song,
    SongSection,
    SectionVersion,
    Line,
    ChordPlacement,
)
from api.enums import SectionType, LineType
from api.services.yjs_schema import sql_song_to_yjs
from api.services.yjs_store import YjsDocumentStore

logger = logging.getLogger(__name__)


class YjsSyncService:
    """
    Sync Yjs documents with SQL database.

    Handles:
    - Initializing Yjs docs from existing SQL data
    - Syncing Yjs changes back to SQL for persistence
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.store = YjsDocumentStore(session)

    async def initialize_yjs_from_sql(self, song_id: UUID) -> Doc:
        """
        Initialize a Yjs document from SQL data.

        Used when a song doesn't have Yjs state yet (first time
        opening in canvas mode).

        Args:
            song_id: The song to initialize

        Returns:
            Yjs Doc populated with song data

        Raises:
            ValueError: If song not found
        """
        # Load song with all relationships
        result = await self.session.execute(
            select(Song)
            .where(Song.id == song_id)
            .options(
                selectinload(Song.sections)
                .selectinload(SongSection.versions)
                .selectinload(SectionVersion.lines)
                .selectinload(Line.chords)
            )
        )
        song = result.scalar_one_or_none()

        if not song:
            raise ValueError(f"Song {song_id} not found")

        # Convert to Yjs
        doc = sql_song_to_yjs(song)

        # Check what canvas content was generated - use doc.get() for proper access
        canvas = doc.get("canvas", type=Text)
        canvas_content = str(canvas) if canvas else ""
        print(f"[YJS] Initialized from SQL, canvas: '{canvas_content[:100]}...' ({len(canvas_content)} chars)")
        print(f"[YJS] Song has {len(song.sections)} sections")

        # Verify doc state before saving
        test_update = doc.get_update()
        print(f"[YJS] Doc update size before save: {len(test_update)} bytes")

        # Persist initial state
        await self.store.save_state(
            song_id=song_id,
            state_vector=doc.get_state(),
            document_state=doc.get_update(),
        )

        # Mark song as Yjs-enabled
        song.yjs_enabled = True
        song.yjs_synced_at = datetime.utcnow()
        await self.session.commit()

        print(f"[YJS] Saved initial state for song {song_id}")
        return doc

    async def get_or_initialize_doc(self, song_id: UUID) -> Doc:
        """
        Get existing Yjs doc or initialize from SQL.

        Args:
            song_id: The song to get/initialize

        Returns:
            Yjs Doc
        """
        # Try to load existing state
        state_vector, doc_state = await self.store.get_state(song_id)

        if doc_state:
            # Existing Yjs state
            doc = Doc()
            doc.apply_update(doc_state)
            # Check canvas content - use doc.get() for proper access
            canvas = doc.get("canvas", type=Text)
            canvas_content = str(canvas) if canvas else ""
            print(f"[YJS] Loaded existing doc for {song_id}, canvas: '{canvas_content[:100]}...' ({len(canvas_content)} chars)")

            # If canvas is empty but song has sections, reinitialize from SQL
            if len(canvas_content) == 0:
                # Check if song has sections in SQL
                result = await self.session.execute(
                    select(Song)
                    .where(Song.id == song_id)
                    .options(selectinload(Song.sections))
                )
                song = result.scalar_one_or_none()
                if song and song.sections:
                    print(f"[YJS] Canvas empty but song has {len(song.sections)} sections, reinitializing from SQL")
                    return await self.initialize_yjs_from_sql(song_id)

            return doc

        # No Yjs state yet - initialize from SQL
        print(f"[YJS] No existing state for {song_id}, initializing from SQL")
        return await self.initialize_yjs_from_sql(song_id)

    async def sync_yjs_to_sql(self, song_id: UUID) -> None:
        """
        Sync Yjs document state to SQL tables.

        Called periodically and on disconnect to ensure SQL
        is up-to-date for AI context, REST API reads, etc.

        Args:
            song_id: The song to sync
        """
        # Load Yjs state
        state_vector, doc_state = await self.store.get_state(song_id)
        if not doc_state:
            logger.warning(f"No Yjs state for song {song_id}")
            return

        # Parse Yjs doc
        doc = Doc()
        doc.apply_update(doc_state)

        # Load current song
        result = await self.session.execute(select(Song).where(Song.id == song_id))
        song = result.scalar_one_or_none()
        if not song:
            logger.warning(f"Song {song_id} not found")
            return

        # Sync meta
        meta = doc["meta"] if "meta" in doc else None
        if meta:
            song.title = meta.get("title") or song.title
            song.key = meta.get("key")
            song.tempo = meta.get("tempo")
            song.time_signature = meta.get("time_signature") or "4/4"
            # Don't sync status from Yjs - that's user-controlled via UI

        # Get existing sections
        result = await self.session.execute(
            select(SongSection)
            .where(SongSection.song_id == song_id)
            .options(selectinload(SongSection.versions))
        )
        existing_sections = {str(s.id): s for s in result.scalars().all()}

        # Sync sections
        sections_array = doc["sections"] if "sections" in doc else None
        if sections_array is None:
            sections_array = []

        yjs_section_ids = set()

        for order, section_map in enumerate(sections_array):
            section_id = section_map.get("id")
            if not section_id:
                continue

            yjs_section_ids.add(section_id)

            section_type_str = section_map.get("type") or "VERSE"
            try:
                section_type = SectionType(section_type_str)
            except ValueError:
                section_type = SectionType.OTHER

            if section_id in existing_sections:
                # Update existing section
                section = existing_sections[section_id]
                section.type = section_type
                section.number = section_map.get("number")
                section.order = order
            else:
                # Create new section
                section = SongSection(
                    id=UUID(section_id),
                    song_id=song_id,
                    type=section_type,
                    number=section_map.get("number"),
                    order=order,
                )
                self.session.add(section)
                await self.session.flush()

                # Create initial version
                version_id = section_map.get("main_version_id")
                version = SectionVersion(
                    id=UUID(version_id) if version_id else None,
                    section_id=section.id,
                    version_number=1,
                    is_main=True,
                )
                self.session.add(version)
                await self.session.flush()

                existing_sections[section_id] = section

            # Sync lines for this section's main version
            await self._sync_lines(
                section=existing_sections[section_id],
                lines_array=section_map.get("lines"),
            )

        # Delete sections that are no longer in Yjs
        for section_id, section in list(existing_sections.items()):
            if section_id not in yjs_section_ids:
                await self.session.delete(section)
                logger.debug(f"Deleted section {section_id} (not in Yjs)")

        # Update sync timestamp
        song.yjs_synced_at = datetime.utcnow()
        await self.session.commit()

        logger.debug(f"Synced Yjs to SQL for song {song_id}")

    async def _sync_lines(
        self,
        section: SongSection,
        lines_array,
    ) -> None:
        """Sync lines for a section's main version."""
        # Get or create main version
        main_version = section.main_version
        if not main_version:
            # Create main version if it doesn't exist
            main_version = SectionVersion(
                section_id=section.id,
                version_number=1,
                is_main=True,
            )
            self.session.add(main_version)
            await self.session.flush()

        # Get existing lines
        result = await self.session.execute(
            select(Line)
            .where(Line.section_version_id == main_version.id)
            .options(selectinload(Line.chords))
        )
        existing_lines = {str(l.id): l for l in result.scalars().all()}

        yjs_line_ids = set()

        for order, line_map in enumerate(lines_array or []):
            line_id = line_map.get("id")
            if not line_id:
                continue

            yjs_line_ids.add(line_id)

            line_type_str = line_map.get("line_type") or "LYRIC"
            try:
                line_type = LineType(line_type_str)
            except ValueError:
                line_type = LineType.LYRIC

            if line_id in existing_lines:
                # Update existing line
                line = existing_lines[line_id]
                line.text = line_map.get("text") or ""
                line.line_type = line_type
                line.order = order
            else:
                # Create new line
                line = Line(
                    id=UUID(line_id),
                    section_version_id=main_version.id,
                    text=line_map.get("text") or "",
                    line_type=line_type,
                    order=order,
                )
                self.session.add(line)
                await self.session.flush()
                existing_lines[line_id] = line

            # Sync chords
            await self._sync_chords(
                line=existing_lines[line_id],
                chords_array=line_map.get("chords"),
            )

        # Delete lines no longer in Yjs
        for line_id, line in list(existing_lines.items()):
            if line_id not in yjs_line_ids:
                await self.session.delete(line)
                logger.debug(f"Deleted line {line_id} (not in Yjs)")

    async def _sync_chords(
        self,
        line: Line,
        chords_array,
    ) -> None:
        """Sync chords for a line."""
        # Delete existing chords and recreate
        # (simpler than diffing for positions)
        await self.session.execute(
            delete(ChordPlacement).where(ChordPlacement.line_id == line.id)
        )

        for chord_map in chords_array or []:
            chord_str = chord_map.get("chord")
            position = chord_map.get("position")

            if chord_str is not None and position is not None:
                chord = ChordPlacement(
                    line_id=line.id,
                    chord=chord_str,
                    position=position,
                )
                self.session.add(chord)
