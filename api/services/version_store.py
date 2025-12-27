"""Database-backed section version store."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models import ChordPlacement, Line, SectionVersion, SongSection


def utc_now() -> datetime:
    """Get current UTC time (Python 3.12+ compatible)."""
    return datetime.now(timezone.utc)


class SectionVersionStore:
    """Database-backed storage for section versions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        section_id: UUID,
        name: Optional[str] = None,
        is_main: bool = False,
    ) -> SectionVersion:
        """Create a new version for a section."""
        # Get next version number
        result = await self.session.execute(
            select(func.max(SectionVersion.version_number))
            .where(SectionVersion.section_id == section_id)
        )
        max_version = result.scalar() or 0
        next_version = max_version + 1

        version = SectionVersion(
            section_id=section_id,
            version_number=next_version,
            name=name,
            is_main=is_main,
        )

        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def get(self, version_id: UUID) -> Optional[SectionVersion]:
        """Get a version by ID with lines loaded."""
        result = await self.session.execute(
            select(SectionVersion)
            .options(
                selectinload(SectionVersion.lines).selectinload(Line.chords),
                selectinload(SectionVersion.audio_files),
            )
            .where(SectionVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def list_by_section(self, section_id: UUID) -> list[SectionVersion]:
        """List all versions for a section."""
        result = await self.session.execute(
            select(SectionVersion)
            .options(
                selectinload(SectionVersion.lines).selectinload(Line.chords),
                selectinload(SectionVersion.audio_files),
            )
            .where(SectionVersion.section_id == section_id)
            .order_by(SectionVersion.version_number)
        )
        return list(result.scalars().all())

    async def update(self, version_id: UUID, updates: dict) -> Optional[SectionVersion]:
        """Update a version's metadata (name, notes)."""
        version = await self.get(version_id)
        if version is None:
            return None

        for key, value in updates.items():
            if hasattr(version, key) and key in ("name", "notes"):
                setattr(version, key, value)

        version.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def delete(self, version_id: UUID) -> bool:
        """Delete a version. Cannot delete the main version if it's the only one."""
        version = await self.get(version_id)
        if version is None:
            return False

        # Check if this is the only version
        result = await self.session.execute(
            select(func.count())
            .select_from(SectionVersion)
            .where(SectionVersion.section_id == version.section_id)
        )
        count = result.scalar() or 0

        if count == 1:
            # Can't delete the last version
            return False

        # If deleting main, promote another version
        if version.is_main:
            result = await self.session.execute(
                select(SectionVersion)
                .where(SectionVersion.section_id == version.section_id)
                .where(SectionVersion.id != version_id)
                .order_by(SectionVersion.version_number)
                .limit(1)
            )
            new_main = result.scalar_one_or_none()
            if new_main:
                new_main.is_main = True

        await self.session.delete(version)
        await self.session.commit()
        return True

    async def duplicate(
        self,
        version_id: UUID,
        name: Optional[str] = None,
    ) -> Optional[SectionVersion]:
        """Duplicate a version with all its lines."""
        source = await self.get(version_id)
        if source is None:
            return None

        # Create new version
        new_version = await self.create(
            section_id=source.section_id,
            name=name or f"Copy of {source.name or f'v{source.version_number}'}",
            is_main=False,
        )

        # Copy lines and their chords
        for line in source.lines:
            new_line = Line(
                section_version_id=new_version.id,
                order=line.order,
                text=line.text,
                notes=line.notes,
            )
            self.session.add(new_line)
            # Flush to get the new line ID
            await self.session.flush()

            # Copy chords for this line
            for chord in line.chords:
                new_chord = ChordPlacement(
                    line_id=new_line.id,
                    chord=chord.chord,
                    position=chord.position,
                )
                self.session.add(new_chord)

        await self.session.commit()
        return await self.get(new_version.id)

    async def promote_to_main(self, version_id: UUID) -> Optional[SectionVersion]:
        """Promote a version to be the main version."""
        version = await self.get(version_id)
        if version is None:
            return None

        if version.is_main:
            return version  # Already main

        # Unset is_main on all other versions for this section
        result = await self.session.execute(
            select(SectionVersion)
            .where(SectionVersion.section_id == version.section_id)
            .where(SectionVersion.is_main == True)
        )
        for old_main in result.scalars().all():
            old_main.is_main = False

        # Set this version as main
        version.is_main = True
        version.updated_at = utc_now()

        await self.session.commit()
        await self.session.refresh(version)
        return version

    async def get_main_version(self, section_id: UUID) -> Optional[SectionVersion]:
        """Get the main version for a section."""
        result = await self.session.execute(
            select(SectionVersion)
            .options(
                selectinload(SectionVersion.lines).selectinload(Line.chords),
                selectinload(SectionVersion.audio_files),
            )
            .where(SectionVersion.section_id == section_id)
            .where(SectionVersion.is_main == True)
        )
        return result.scalar_one_or_none()

    async def ensure_main_version(self, section_id: UUID) -> SectionVersion:
        """Ensure a section has a main version, creating one if needed."""
        main = await self.get_main_version(section_id)
        if main:
            return main

        # Create default main version
        return await self.create(
            section_id=section_id,
            name="Original",
            is_main=True,
        )
