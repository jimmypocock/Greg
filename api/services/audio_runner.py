"""
Background audio analysis runner service.

Runs audio analysis tasks asynchronously and streams updates via WebSocket.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from api.enums import AnalysisStatus
from api.services.audio_analysis import (
    analyze_audio,
    beats_to_json,
    chords_to_json,
)
from api.services.audio_store import AudioFileStore
from api.database import get_session
from api.jobs import job_manager
from api.jobs.models import JobType
from api.websocket import connection_manager

logger = logging.getLogger(__name__)


def _task_exception_handler(task: asyncio.Task[Any]) -> None:
    """Handle exceptions from background tasks to prevent silent failures."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error(f"Background task {task.get_name()} failed with unhandled exception: {exc}")


async def run_audio_analysis_task(
    audio_file_id: UUID,
    file_path: Path,
    user_id: UUID,
) -> str:
    """
    Run an audio analysis task with WebSocket streaming.

    Args:
        audio_file_id: ID of the audio file record
        file_path: Path to the audio file
        user_id: ID of the user running the task

    Returns:
        task_id that can be used to track progress via WebSocket
    """
    job = await job_manager.create_job(JobType.AUDIO_ANALYSIS, user_id)
    task_id = job.job_id

    # Run analysis in background with exception handling
    task = asyncio.create_task(
        _run_audio_analysis_async(
            task_id=task_id,
            audio_file_id=audio_file_id,
            file_path=file_path,
        ),
        name=f"audio_analysis_{task_id}",
    )
    task.add_done_callback(_task_exception_handler)

    return task_id


async def _run_audio_analysis_async(
    task_id: str,
    audio_file_id: UUID,
    file_path: Path,
) -> None:
    """Run the audio analysis asynchronously with streaming updates."""
    try:
        # Broadcast start event
        await connection_manager.broadcast_to_job(
            task_id,
            {
                "event": "audio.started",
                "data": {
                    "task_id": task_id,
                    "audio_file_id": str(audio_file_id),
                    "message": "Starting audio analysis...",
                },
            },
        )

        # Update job status to running
        await job_manager.update_progress(task_id, "analyzing", 10, "Loading audio file...")

        # Broadcast analyzing event
        await connection_manager.broadcast_to_job(
            task_id,
            {
                "event": "audio.analyzing",
                "data": {
                    "task_id": task_id,
                    "audio_file_id": str(audio_file_id),
                    "stage": "loading",
                    "progress": 10,
                    "message": "Loading audio file...",
                },
            },
        )

        # Run analysis in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_audio, file_path)

        if not result.success:
            raise Exception(result.error or "Analysis failed")

        # Convert chords and beats to JSON for storage
        chords_json = chords_to_json(result.chords) if result.chords else None
        beats_json = beats_to_json(result.beat_positions) if result.beat_positions else None

        # Update database with results
        async with get_session() as session:
            audio_store = AudioFileStore(session)
            await audio_store.update_analysis_results(
                audio_file_id=audio_file_id,
                tempo=result.tempo,
                tempo_confidence=result.tempo_confidence,
                key=result.key,
                key_confidence=result.key_confidence,
                duration_seconds=result.duration_seconds,
                time_signature=result.time_signature,
                time_signature_confidence=result.time_signature_confidence,
                detected_chords=chords_json,
                beat_positions=beats_json,
            )

        # Broadcast completion
        await connection_manager.broadcast_to_job(
            task_id,
            {
                "event": "audio.completed",
                "data": {
                    "task_id": task_id,
                    "audio_file_id": str(audio_file_id),
                    "tempo": result.tempo,
                    "tempo_confidence": result.tempo_confidence,
                    "key": result.key,
                    "key_confidence": result.key_confidence,
                    "duration_seconds": result.duration_seconds,
                    "time_signature": result.time_signature,
                    "time_signature_confidence": result.time_signature_confidence,
                    "chord_count": len(result.chords),
                    "beat_count": len(result.beat_positions),
                },
            },
        )

        # Complete the job with results
        await job_manager.complete_job(
            task_id,
            {
                "audio_file_id": str(audio_file_id),
                "tempo": result.tempo,
                "tempo_confidence": result.tempo_confidence,
                "key": result.key,
                "key_confidence": result.key_confidence,
                "duration_seconds": result.duration_seconds,
                "time_signature": result.time_signature,
                "time_signature_confidence": result.time_signature_confidence,
                "chord_count": len(result.chords),
                "beat_count": len(result.beat_positions),
                "success": True,
            },
        )

        logger.info(
            f"Audio analysis completed for {audio_file_id}: "
            f"tempo={result.tempo}, key={result.key}, time_sig={result.time_signature}, "
            f"chords={len(result.chords)}, beats={len(result.beat_positions)}"
        )

    except Exception as e:
        logger.error(f"Audio analysis task {task_id} failed: {e}")

        # Update database with failure
        try:
            async with get_session() as session:
                audio_store = AudioFileStore(session)
                await audio_store.update_analysis_status(
                    audio_file_id, AnalysisStatus.FAILED, str(e)
                )
        except Exception as db_err:
            logger.error(f"Failed to update analysis status: {db_err}")

        # Broadcast failure
        await connection_manager.broadcast_to_job(
            task_id,
            {
                "event": "audio.failed",
                "data": {
                    "task_id": task_id,
                    "audio_file_id": str(audio_file_id),
                    "error": str(e),
                },
            },
        )

        # Fail the job
        await job_manager.fail_job(task_id, str(e))
