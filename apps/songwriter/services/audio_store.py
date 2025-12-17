"""
Database store for audio files.

Handles CRUD operations for AudioFile records.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.songwriter.enums import AnalysisStatus
from apps.songwriter.models import AudioFile

logger = logging.getLogger(__name__)


class AudioFileStore:
    """Database store for audio file operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, audio_file: AudioFile) -> AudioFile:
        """Create a new audio file record."""
        self.session.add(audio_file)
        await self.session.commit()
        await self.session.refresh(audio_file)
        logger.info(f"Created audio file: {audio_file.filename} ({audio_file.id})")
        return audio_file

    async def get(self, audio_file_id: UUID) -> AudioFile | None:
        """Get an audio file by ID."""
        result = await self.session.execute(
            select(AudioFile).where(AudioFile.id == audio_file_id)
        )
        return result.scalar_one_or_none()

    async def get_by_song(self, song_id: UUID) -> list[AudioFile]:
        """Get all audio files for a song."""
        result = await self.session.execute(
            select(AudioFile)
            .where(AudioFile.song_id == song_id)
            .order_by(AudioFile.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, audio_file_id: UUID, updates: dict) -> AudioFile | None:
        """Update an audio file record."""
        audio_file = await self.get(audio_file_id)
        if not audio_file:
            return None

        for key, value in updates.items():
            setattr(audio_file, key, value)

        await self.session.commit()
        await self.session.refresh(audio_file)
        return audio_file

    async def update_analysis_status(
        self,
        audio_file_id: UUID,
        status: AnalysisStatus,
        error: str | None = None,
    ) -> AudioFile | None:
        """Update the analysis status of an audio file."""
        updates = {"analysis_status": status}
        if error:
            updates["analysis_error"] = error
        return await self.update(audio_file_id, updates)

    async def update_analysis_results(
        self,
        audio_file_id: UUID,
        tempo: float | None,
        tempo_confidence: float | None,
        key: str | None,
        key_confidence: float | None,
        duration_seconds: float | None,
    ) -> AudioFile | None:
        """Update the analysis results of an audio file."""
        return await self.update(
            audio_file_id,
            {
                "detected_tempo": tempo,
                "confidence_tempo": tempo_confidence,
                "detected_key": key,
                "confidence_key": key_confidence,
                "duration_seconds": duration_seconds,
                "analysis_status": AnalysisStatus.COMPLETED,
                "analysis_error": None,
            },
        )

    async def delete(self, audio_file_id: UUID) -> bool:
        """Delete an audio file record."""
        audio_file = await self.get(audio_file_id)
        if not audio_file:
            return False

        await self.session.delete(audio_file)
        await self.session.commit()
        logger.info(f"Deleted audio file: {audio_file_id}")
        return True

    async def get_reference_for_song(self, song_id: UUID) -> AudioFile | None:
        """Get the reference audio file for a song (if any)."""
        result = await self.session.execute(
            select(AudioFile)
            .where(AudioFile.song_id == song_id)
            .where(AudioFile.is_reference == True)
            .limit(1)
        )
        return result.scalar_one_or_none()
