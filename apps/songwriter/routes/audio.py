"""
Audio file routes for the Songwriter app.

Endpoints:
    POST   /songs/{song_id}/audio              - Upload an audio file
    GET    /songs/{song_id}/audio              - List audio files for a song
    GET    /songs/{song_id}/audio/{audio_id}   - Get an audio file
    DELETE /songs/{song_id}/audio/{audio_id}   - Delete an audio file
    POST   /songs/{song_id}/audio/{audio_id}/analyze - Start analysis
    POST   /songs/{song_id}/audio/{audio_id}/apply   - Apply analysis to song
"""

import logging
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.songwriter.enums import AnalysisStatus
from apps.songwriter.models import AudioFile
from apps.songwriter.services.audio_runner import run_audio_analysis_task
from apps.songwriter.services.audio_store import AudioFileStore
from apps.songwriter.services.db_store import SongDBStore
from packages.core.database import get_session_dependency

logger = logging.getLogger(__name__)

# Anonymous user ID for standalone songwriter app (no auth)
ANONYMOUS_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")

# Upload directory for audio files
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads")) / "audio"

# Allowed audio MIME types
ALLOWED_MIME_TYPES = {
    "audio/mpeg": [".mp3"],
    "audio/mp3": [".mp3"],
    "audio/wav": [".wav"],
    "audio/x-wav": [".wav"],
    "audio/wave": [".wav"],
    "audio/x-m4a": [".m4a"],
    "audio/mp4": [".m4a"],
    "audio/aac": [".aac"],
}

# Max file size (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

router = APIRouter(prefix="/songs/{song_id}/audio", tags=["Audio"])


# Dependencies

async def get_db_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongDBStore:
    """Get a database-backed song store."""
    return SongDBStore(session)


async def get_audio_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> AudioFileStore:
    """Get a database-backed audio file store."""
    return AudioFileStore(session)


# Response models

class AudioFileResponse(BaseModel):
    """Response for an audio file."""

    id: uuid.UUID
    song_id: uuid.UUID
    section_version_id: Optional[uuid.UUID]
    filename: str
    display_name: Optional[str]
    mime_type: str
    file_size_bytes: int
    duration_seconds: Optional[float]
    detected_tempo: Optional[float]
    detected_key: Optional[str]
    detected_time_signature: Optional[str]
    confidence_tempo: Optional[float]
    confidence_key: Optional[float]
    analysis_status: AnalysisStatus
    analysis_error: Optional[str]
    is_reference: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AudioFileListResponse(BaseModel):
    """Response for listing audio files."""

    audio_files: list[AudioFileResponse]
    total: int


class AudioUploadResponse(BaseModel):
    """Response after uploading an audio file."""

    audio_file: AudioFileResponse
    message: str = "Audio file uploaded successfully"


class AnalysisTaskResponse(BaseModel):
    """Response when an analysis task is started."""

    task_id: str = Field(..., description="Task ID to track progress via WebSocket")
    audio_file_id: uuid.UUID
    message: str = "Analysis started. Connect to WebSocket for progress updates."
    websocket_url: str = Field(..., description="WebSocket URL for progress updates")


class ApplyAnalysisResponse(BaseModel):
    """Response after applying analysis results to a song."""

    message: str
    tempo_applied: Optional[int] = None
    key_applied: Optional[str] = None


class UpdateAudioFileRequest(BaseModel):
    """Request to update an audio file's metadata."""

    display_name: Optional[str] = Field(None, max_length=255)
    is_reference: Optional[bool] = None


# Routes

@router.post("/", response_model=AudioUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    song_id: uuid.UUID,
    file: UploadFile = File(...),
    is_reference: bool = Form(False),
    section_version_id: Optional[uuid.UUID] = Form(None),
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """
    Upload an audio file for a song.

    The file will be stored and can later be analyzed for tempo/key detection.
    If is_reference is True, the detected values will be automatically applied
    to the song metadata when analysis completes.

    Optionally, attach the audio to a specific section version by providing
    section_version_id. If not provided, the audio is song-level.
    """
    # Verify song exists
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    # Validate file type
    content_type = file.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid file type: {content_type}. Allowed: mp3, wav, m4a",
        )

    # Read file content to check size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Create storage directory
    song_dir = UPLOAD_DIR / str(song_id)
    song_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_ext = Path(file.filename or "audio.mp3").suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    storage_path = song_dir / unique_filename

    # Write file
    with open(storage_path, "wb") as f:
        f.write(content)

    logger.info(f"Saved audio file: {storage_path} ({len(content)} bytes)")

    # If setting as reference, unset any existing reference
    if is_reference:
        existing_ref = await audio_store.get_reference_for_song(song_id)
        if existing_ref:
            await audio_store.update(existing_ref.id, {"is_reference": False})

    # Create database record
    audio_file = AudioFile(
        song_id=song_id,
        section_version_id=section_version_id,
        filename=file.filename or "audio",
        storage_path=str(storage_path),
        mime_type=content_type,
        file_size_bytes=len(content),
        is_reference=is_reference,
        analysis_status=AnalysisStatus.PENDING,
    )

    audio_file = await audio_store.create(audio_file)

    return AudioUploadResponse(
        audio_file=AudioFileResponse.model_validate(audio_file),
    )


@router.get("/", response_model=AudioFileListResponse)
async def list_audio_files(
    song_id: uuid.UUID,
    section_version_id: Optional[uuid.UUID] = None,
    song_level_only: bool = False,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """
    List audio files for a song.

    Query params:
    - section_version_id: Filter to audio files attached to this version
    - song_level_only: If true, only return audio files with no version (song-level)
    """
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_files = await audio_store.get_by_song(
        song_id,
        section_version_id=section_version_id,
        song_level_only=song_level_only,
    )

    return AudioFileListResponse(
        audio_files=[AudioFileResponse.model_validate(af) for af in audio_files],
        total=len(audio_files),
    )


@router.get("/{audio_id}", response_model=AudioFileResponse)
async def get_audio_file(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """Get an audio file by ID."""
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_file = await audio_store.get(audio_id)
    if not audio_file or audio_file.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found")

    return AudioFileResponse.model_validate(audio_file)


@router.put("/{audio_id}", response_model=AudioFileResponse)
async def update_audio_file(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    request: UpdateAudioFileRequest,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """Update an audio file's metadata (display name, reference status)."""
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_file = await audio_store.get(audio_id)
    if not audio_file or audio_file.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found")

    # Build updates
    updates = {}
    if request.display_name is not None:
        updates["display_name"] = request.display_name or None  # Empty string becomes None
    if request.is_reference is not None:
        # If setting as reference, unset any existing reference
        if request.is_reference:
            existing_ref = await audio_store.get_reference_for_song(song_id)
            if existing_ref and existing_ref.id != audio_id:
                await audio_store.update(existing_ref.id, {"is_reference": False})
        updates["is_reference"] = request.is_reference

    if updates:
        audio_file = await audio_store.update(audio_id, updates)
        logger.info(f"Updated audio file {audio_id}: {updates}")

    return AudioFileResponse.model_validate(audio_file)


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio_file(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """Delete an audio file."""
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_file = await audio_store.get(audio_id)
    if not audio_file or audio_file.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found")

    # Delete the actual file
    storage_path = Path(audio_file.storage_path)
    if storage_path.exists():
        storage_path.unlink()
        logger.info(f"Deleted file: {storage_path}")

    # Delete database record
    await audio_store.delete(audio_id)

    logger.info(f"Deleted audio file: {audio_id}")


@router.get("/{audio_id}/stream")
async def stream_audio_file(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """
    Stream an audio file for playback.

    Returns the audio file with appropriate headers for browser playback.
    """
    from fastapi.responses import FileResponse

    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_file = await audio_store.get(audio_id)
    if not audio_file or audio_file.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found")

    storage_path = Path(audio_file.storage_path)
    if not storage_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found on disk")

    return FileResponse(
        path=storage_path,
        media_type=audio_file.mime_type,
        filename=audio_file.filename,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
        },
    )


@router.post("/{audio_id}/analyze", response_model=AnalysisTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_audio_file(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """
    Start analysis of an audio file.

    Returns immediately with a task_id. Connect to the WebSocket
    at /ws/jobs/{task_id} for real-time progress updates.
    """
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_file = await audio_store.get(audio_id)
    if not audio_file or audio_file.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found")

    # Check if file exists
    storage_path = Path(audio_file.storage_path)
    if not storage_path.exists():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Audio file not found on disk. Please re-upload.",
        )

    # Update status to analyzing
    await audio_store.update_analysis_status(audio_id, AnalysisStatus.ANALYZING)

    # Start analysis task
    task_id = await run_audio_analysis_task(
        audio_file_id=audio_id,
        file_path=storage_path,
        user_id=ANONYMOUS_USER_ID,
    )

    logger.info(f"Started audio analysis for {audio_id}, task_id={task_id}")

    return AnalysisTaskResponse(
        task_id=task_id,
        audio_file_id=audio_id,
        websocket_url=f"/ws/jobs/{task_id}",
    )


@router.post("/{audio_id}/apply", response_model=ApplyAnalysisResponse)
async def apply_analysis_to_song(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """
    Apply the analysis results from an audio file to the song metadata.

    This will update the song's tempo and key based on the detected values.
    """
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_file = await audio_store.get(audio_id)
    if not audio_file or audio_file.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found")

    if audio_file.analysis_status != AnalysisStatus.COMPLETED:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Analysis not complete. Status: {audio_file.analysis_status.value}",
        )

    # Build updates
    updates = {}
    tempo_applied = None
    key_applied = None

    if audio_file.detected_tempo:
        updates["tempo"] = int(round(audio_file.detected_tempo))
        tempo_applied = updates["tempo"]

    if audio_file.detected_key:
        # Convert "C Major" to just "C" or keep full if minor
        key = audio_file.detected_key
        if " Major" in key:
            key = key.replace(" Major", "")
        elif " Minor" in key:
            key = key.replace(" Minor", "m")
        updates["key"] = key
        key_applied = key

    if not updates:
        return ApplyAnalysisResponse(
            message="No analysis results to apply",
        )

    await store.update(song_id, updates)

    logger.info(f"Applied analysis to song {song_id}: tempo={tempo_applied}, key={key_applied}")

    return ApplyAnalysisResponse(
        message="Analysis results applied to song",
        tempo_applied=tempo_applied,
        key_applied=key_applied,
    )
