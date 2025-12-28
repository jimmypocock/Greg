"""Song shape service for new song exploration sessions.

The song shape captures the creative structure discovered during exploration:
- Theme and key imagery
- Emotional arc
- References and influences
- Suggested section structure

The shape is stored as a JSON note with NoteType.SONG_SHAPE.

NOTE: This service uses a session factory pattern to support concurrent
database operations. Each method creates its own session, which is required
when pydantic-ai calls multiple tools in parallel.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.enums import NoteType, SectionType
from api.models import SongNote, SongSection


logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Get current UTC time (Python 3.12+ compatible)."""
    return datetime.now(timezone.utc)


# Type alias for session factory
SessionFactory = Callable[[], AsyncSession]


# =============================================================================
# Shape data models
# =============================================================================


class KeyImage(BaseModel):
    """A key image or phrase discovered during exploration."""

    text: str
    category: str = "general"  # e.g., "visual", "emotional", "temporal"
    notes: Optional[str] = None


class EmotionalArc(BaseModel):
    """The emotional journey of the song."""

    start: str = ""  # e.g., "pain", "longing"
    end: str = ""  # e.g., "hope", "acceptance"
    turning_point: Optional[str] = None  # e.g., "the realization"
    notes: Optional[str] = None


class SuggestedSection(BaseModel):
    """A suggested section from the song shape."""

    type: SectionType
    intent: str = ""  # e.g., "Set the scene - the memory"
    key_images: list[str] = Field(default_factory=list)


class Reference(BaseModel):
    """A reference song, artist, or influence."""

    name: str
    aspect: str = ""  # e.g., "melodic vibe", "lyrical style", "emotional feel"


class SongShape(BaseModel):
    """The complete shape of a song discovered during exploration.

    This represents the creative structure without any actual lyrics.
    It's built incrementally through conversation with the song shaper agent.
    """

    # Core theme
    theme: str = ""
    theme_notes: Optional[str] = None

    # Key imagery and phrases
    key_images: list[KeyImage] = Field(default_factory=list)

    # Emotional journey
    emotional_arc: EmotionalArc = Field(default_factory=EmotionalArc)

    # References and influences
    references: list[Reference] = Field(default_factory=list)

    # Suggested structure
    suggested_structure: list[SuggestedSection] = Field(default_factory=list)

    # Conversation insights
    raw_fragments: list[str] = Field(default_factory=list)  # User's raw phrases/lines
    conversation_summary: Optional[str] = None

    def is_ready_for_writing(self) -> bool:
        """Check if the shape has enough to transition to writing."""
        return bool(
            self.theme
            and len(self.suggested_structure) >= 2
            and (self.emotional_arc.start or self.emotional_arc.end)
        )

    def to_ai_context(self) -> str:
        """Format the shape for AI consumption."""
        lines = ["## Song Shape"]

        if self.theme:
            lines.append(f"\n**Theme:** {self.theme}")
            if self.theme_notes:
                lines.append(f"  Notes: {self.theme_notes}")

        if self.emotional_arc.start or self.emotional_arc.end:
            lines.append("\n**Emotional Arc:**")
            if self.emotional_arc.start:
                lines.append(f"  Start: {self.emotional_arc.start}")
            if self.emotional_arc.end:
                lines.append(f"  End: {self.emotional_arc.end}")
            if self.emotional_arc.turning_point:
                lines.append(f"  Turning point: {self.emotional_arc.turning_point}")

        if self.key_images:
            lines.append("\n**Key Images:**")
            for img in self.key_images:
                cat_note = f" ({img.category})" if img.category != "general" else ""
                lines.append(f"  - {img.text}{cat_note}")

        if self.references:
            lines.append("\n**References:**")
            for ref in self.references:
                aspect_note = f" - {ref.aspect}" if ref.aspect else ""
                lines.append(f"  - {ref.name}{aspect_note}")

        if self.suggested_structure:
            lines.append("\n**Suggested Structure:**")
            for i, section in enumerate(self.suggested_structure, 1):
                lines.append(f"  {i}. {section.type.value.upper()}: {section.intent}")

        if self.raw_fragments:
            lines.append("\n**User's Fragments:**")
            for frag in self.raw_fragments:
                lines.append(f"  - \"{frag}\"")

        return "\n".join(lines)


# =============================================================================
# Shape service
# =============================================================================


class SongShapeService:
    """Service for managing song shapes stored in song_notes.

    This service uses a session factory pattern to support concurrent
    database operations. Each method creates its own session, which is
    essential when pydantic-ai calls multiple tools in parallel.
    """

    def __init__(self, session_factory: SessionFactory):
        """Initialize with a session factory.

        Args:
            session_factory: A callable that returns a new AsyncSession.
                            Use `get_session` from api.database for this.
        """
        self._session_factory = session_factory

    async def get_shape(self, song_id: UUID) -> Optional[SongShape]:
        """Get the song shape for a song, if it exists."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(SongNote)
                .where(SongNote.song_id == song_id)
                .where(SongNote.note_type == NoteType.SONG_SHAPE)
                .order_by(SongNote.created_at.desc())
                .limit(1)
            )
            note = result.scalar_one_or_none()

            if note is None:
                return None

            try:
                data = json.loads(note.content)
                return SongShape(**data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse song shape for {song_id}: {e}")
                return SongShape()

    async def create_shape(self, song_id: UUID) -> SongShape:
        """Create an empty song shape for a song."""
        async with self._session_factory() as session:
            shape = SongShape()
            note = SongNote(
                song_id=song_id,
                note_type=NoteType.SONG_SHAPE,
                title="Song Shape",
                content=shape.model_dump_json(),
            )
            session.add(note)
            await session.commit()
            return shape

    async def update_shape(self, song_id: UUID, updates: dict) -> SongShape:
        """Update the song shape with new data.

        Args:
            song_id: The song ID
            updates: Dictionary of fields to update (merged with existing shape)

        Returns:
            The updated SongShape
        """
        async with self._session_factory() as session:
            # Get existing shape
            result = await session.execute(
                select(SongNote)
                .where(SongNote.song_id == song_id)
                .where(SongNote.note_type == NoteType.SONG_SHAPE)
                .order_by(SongNote.created_at.desc())
                .limit(1)
            )
            note = result.scalar_one_or_none()

            if note is None:
                existing = SongShape()
            else:
                try:
                    data = json.loads(note.content)
                    existing = SongShape(**data)
                except (json.JSONDecodeError, ValueError):
                    existing = SongShape()

            # Merge updates into existing shape
            existing_data = existing.model_dump()

            # Handle list fields specially - append rather than replace
            for key in ["key_images", "references", "raw_fragments"]:
                if key in updates:
                    if isinstance(updates[key], list):
                        existing_data[key] = existing_data.get(key, []) + updates[key]
                        updates.pop(key)

            # Handle suggested_structure - can replace or append
            if "suggested_structure" in updates:
                if updates.get("replace_structure", False):
                    existing_data["suggested_structure"] = updates["suggested_structure"]
                else:
                    existing_data["suggested_structure"] = (
                        existing_data.get("suggested_structure", [])
                        + updates["suggested_structure"]
                    )
                updates.pop("suggested_structure", None)
                updates.pop("replace_structure", None)

            # Handle emotional_arc - merge sub-fields
            if "emotional_arc" in updates:
                arc_updates = updates.pop("emotional_arc")
                existing_arc = existing_data.get("emotional_arc", {})
                for k, v in arc_updates.items():
                    if v:  # Only update non-empty values
                        existing_arc[k] = v
                existing_data["emotional_arc"] = existing_arc

            # Apply remaining updates
            for key, value in updates.items():
                if value is not None:
                    existing_data[key] = value

            updated_shape = SongShape(**existing_data)

            # Upsert the note
            if note:
                note.content = updated_shape.model_dump_json()
                note.updated_at = utc_now()
            else:
                note = SongNote(
                    song_id=song_id,
                    note_type=NoteType.SONG_SHAPE,
                    title="Song Shape",
                    content=updated_shape.model_dump_json(),
                )
                session.add(note)

            await session.commit()
            return updated_shape

    async def add_fragment(self, song_id: UUID, fragment: str) -> SongShape:
        """Add a user fragment to the shape."""
        return await self.update_shape(song_id, {"raw_fragments": [fragment]})

    async def add_key_image(
        self,
        song_id: UUID,
        text: str,
        category: str = "general",
        notes: Optional[str] = None,
    ) -> SongShape:
        """Add a key image to the shape."""
        return await self.update_shape(
            song_id,
            {"key_images": [{"text": text, "category": category, "notes": notes}]},
        )

    async def set_emotional_arc(
        self,
        song_id: UUID,
        start: Optional[str] = None,
        end: Optional[str] = None,
        turning_point: Optional[str] = None,
    ) -> SongShape:
        """Update the emotional arc."""
        arc_updates = {}
        if start:
            arc_updates["start"] = start
        if end:
            arc_updates["end"] = end
        if turning_point:
            arc_updates["turning_point"] = turning_point
        return await self.update_shape(song_id, {"emotional_arc": arc_updates})

    async def set_suggested_structure(
        self,
        song_id: UUID,
        sections: list[dict],
        replace: bool = True,
    ) -> SongShape:
        """Set or append to the suggested structure.

        Args:
            song_id: The song ID
            sections: List of section dicts with 'type', 'intent', 'key_images'
            replace: If True, replace existing structure; if False, append
        """
        return await self.update_shape(
            song_id,
            {
                "suggested_structure": sections,
                "replace_structure": replace,
            },
        )

    async def create_sections_from_shape(
        self,
        song_id: UUID,
        db_store,  # SongDBStore - avoid circular import
    ) -> list[SongSection]:
        """Create actual song sections from the suggested structure.

        This finalizes the exploration phase and transitions to writing.

        Args:
            song_id: The song ID
            db_store: SongDBStore instance for creating sections

        Returns:
            List of created SongSection objects
        """
        shape = await self.get_shape(song_id)
        if shape is None or not shape.suggested_structure:
            return []

        created_sections = []

        for i, suggested in enumerate(shape.suggested_structure):
            section = SongSection(
                type=suggested.type,
                number=self._get_section_number(suggested.type, created_sections),
                order=i,
                notes=suggested.intent,
            )

            await db_store.add_section(song_id, section)
            created_sections.append(section)

        logger.info(
            f"Created {len(created_sections)} sections from shape for song {song_id}"
        )
        return created_sections

    def _get_section_number(
        self,
        section_type: SectionType,
        existing: list[SongSection],
    ) -> int:
        """Calculate the section number based on how many of that type exist."""
        count = sum(1 for s in existing if s.type == section_type)
        return count + 1

    async def delete_shape(self, song_id: UUID) -> bool:
        """Delete the song shape note."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(SongNote)
                .where(SongNote.song_id == song_id)
                .where(SongNote.note_type == NoteType.SONG_SHAPE)
            )
            note = result.scalar_one_or_none()

            if note is None:
                return False

            await session.delete(note)
            await session.commit()
            return True
