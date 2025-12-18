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

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.songwriter.constants import (
    ALLOWED_AUDIO_MIME_TYPES,
    AUDIO_FILE_SIGNATURES,
    AUDIO_UPLOAD_DIR,
    MAX_AUDIO_FILE_SIZE_BYTES,
    MAX_AUDIO_FILE_SIZE_MB,
)
from apps.songwriter.dependencies import PermissionService
from apps.songwriter.enums import AnalysisStatus
from apps.songwriter.models import AudioFile
from apps.songwriter.services.audio_runner import run_audio_analysis_task
from apps.songwriter.services.audio_store import AudioFileStore
from apps.songwriter.services.db_store import SongDBStore
from apps.songwriter.services.permissions import Permission
from packages.core.auth import CurrentUser
from packages.core.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/songs/{song_id}/audio", tags=["Audio"])


def validate_audio_file_content(content: bytes, claimed_mime_type: str) -> str | None:
    """
    Validate audio file content using magic bytes.

    Args:
        content: File content bytes
        claimed_mime_type: MIME type claimed by the upload

    Returns:
        Detected MIME type if valid, None if invalid
    """
    if len(content) < 12:
        return None

    # Check for MP3 signatures
    if content[:3] == b"ID3" or content[:2] in (b"\xff\xfb", b"\xff\xfa", b"\xff\xf3", b"\xff\xf2"):
        return "audio/mpeg"

    # Check for WAV (RIFF header)
    if content[:4] == b"RIFF" and content[8:12] == b"WAVE":
        return "audio/wav"

    # Check for M4A/MP4 (ftyp box at offset 4)
    if content[4:8] == b"ftyp":
        return "audio/mp4"

    # If we can't detect from magic bytes, trust the claimed type
    # but only if it's in our allowed list
    if claimed_mime_type in ALLOWED_AUDIO_MIME_TYPES:
        return claimed_mime_type

    return None


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

class ChordDetection(BaseModel):
    """A detected chord at a specific time range."""

    start: float
    end: float
    chord: str


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
    confidence_time_signature: Optional[float]
    detected_chords: Optional[list[ChordDetection]]
    beat_positions: Optional[list[float]]
    analysis_status: AnalysisStatus
    analysis_error: Optional[str]
    is_reference: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_db(cls, audio_file) -> "AudioFileResponse":
        """Create response from database model, parsing JSON fields."""
        # Type adapters for validated parsing
        chords_adapter = TypeAdapter(list[ChordDetection])
        beats_adapter = TypeAdapter(list[float])

        # Parse chords JSON with Pydantic validation
        chords = None
        detected_chords_raw = getattr(audio_file, 'detected_chords', None)
        if detected_chords_raw:
            try:
                chords_data = json.loads(detected_chords_raw)
                chords = chords_adapter.validate_python(chords_data)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Failed to parse detected_chords for audio {audio_file.id}: {e}")
                chords = None

        # Parse beats JSON with Pydantic validation
        beats = None
        beat_positions_raw = getattr(audio_file, 'beat_positions', None)
        if beat_positions_raw:
            try:
                beats_data = json.loads(beat_positions_raw)
                beats = beats_adapter.validate_python(beats_data)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Failed to parse beat_positions for audio {audio_file.id}: {e}")
                beats = None

        return cls(
            id=audio_file.id,
            song_id=audio_file.song_id,
            section_version_id=audio_file.section_version_id,
            filename=audio_file.filename,
            display_name=audio_file.display_name,
            mime_type=audio_file.mime_type,
            file_size_bytes=audio_file.file_size_bytes,
            duration_seconds=audio_file.duration_seconds,
            detected_tempo=audio_file.detected_tempo,
            detected_key=audio_file.detected_key,
            detected_time_signature=getattr(audio_file, 'detected_time_signature', None),
            confidence_tempo=audio_file.confidence_tempo,
            confidence_key=audio_file.confidence_key,
            confidence_time_signature=getattr(audio_file, 'confidence_time_signature', None),
            detected_chords=chords,
            beat_positions=beats,
            analysis_status=audio_file.analysis_status,
            analysis_error=audio_file.analysis_error,
            is_reference=audio_file.is_reference,
            created_at=audio_file.created_at,
            updated_at=audio_file.updated_at,
        )


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
    user: CurrentUser,
    permission_service: PermissionService,
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
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    # Verify song exists
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    # Read file content first to validate
    content = await file.read()

    # Validate file size
    if len(content) > MAX_AUDIO_FILE_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"File too large. Maximum size is {MAX_AUDIO_FILE_SIZE_MB}MB",
        )

    # Validate file type using both header and magic bytes
    claimed_type = file.content_type or ""
    validated_type = validate_audio_file_content(content, claimed_type)

    if not validated_type:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Invalid or unrecognized audio file. Allowed formats: mp3, wav, m4a, aac",
        )

    # Create storage directory
    song_dir = AUDIO_UPLOAD_DIR / str(song_id)
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
        mime_type=validated_type,
        file_size_bytes=len(content),
        is_reference=is_reference,
        analysis_status=AnalysisStatus.PENDING,
    )

    audio_file = await audio_store.create(audio_file)

    return AudioUploadResponse(
        audio_file=AudioFileResponse.from_db(audio_file),
    )


@router.get("/", response_model=AudioFileListResponse)
async def list_audio_files(
    song_id: uuid.UUID,
    user: CurrentUser,
    permission_service: PermissionService,
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
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_files = await audio_store.get_by_song(
        song_id,
        section_version_id=section_version_id,
        song_level_only=song_level_only,
    )

    return AudioFileListResponse(
        audio_files=[AudioFileResponse.from_db(af) for af in audio_files],
        total=len(audio_files),
    )


@router.get("/{audio_id}", response_model=AudioFileResponse)
async def get_audio_file(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """Get an audio file by ID."""
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    audio_file = await audio_store.get(audio_id)
    if not audio_file or audio_file.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Audio file not found")

    return AudioFileResponse.from_db(audio_file)


@router.put("/{audio_id}", response_model=AudioFileResponse)
async def update_audio_file(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    request: UpdateAudioFileRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """Update an audio file's metadata (display name, reference status)."""
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

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

    return AudioFileResponse.from_db(audio_file)


@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audio_file(
    song_id: uuid.UUID,
    audio_id: uuid.UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """Delete an audio file."""
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

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
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """
    Stream an audio file for playback.

    Returns the audio file with appropriate headers for browser playback.
    """
    from fastapi.responses import FileResponse

    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

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
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """
    Start analysis of an audio file.

    Returns immediately with a task_id. Connect to the WebSocket
    at /ws/jobs/{task_id} for real-time progress updates.
    """
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

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
        user_id=user.id,
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
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    audio_store: AudioFileStore = Depends(get_audio_store),
):
    """
    Apply the analysis results from an audio file to the song metadata.

    This will update the song's tempo and key based on the detected values.
    """
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

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
