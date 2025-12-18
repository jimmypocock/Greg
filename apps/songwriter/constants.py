"""
Shared constants for the Songwriter app.

Centralizes configuration values, limits, and magic numbers
to make the codebase more maintainable.
"""

import os
from pathlib import Path
from uuid import UUID

# =============================================================================
# Upload and Storage
# =============================================================================

# Upload directory for audio files
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads"))
AUDIO_UPLOAD_DIR = UPLOAD_DIR / "audio"

# Max audio file size in bytes (default: 50MB)
MAX_AUDIO_FILE_SIZE_MB = int(os.environ.get("MAX_AUDIO_FILE_SIZE_MB", "50"))
MAX_AUDIO_FILE_SIZE_BYTES = MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024

# Allowed audio MIME types with their file extensions
ALLOWED_AUDIO_MIME_TYPES = {
    "audio/mpeg": [".mp3"],
    "audio/mp3": [".mp3"],
    "audio/wav": [".wav"],
    "audio/x-wav": [".wav"],
    "audio/wave": [".wav"],
    "audio/x-m4a": [".m4a"],
    "audio/mp4": [".m4a"],
    "audio/aac": [".aac"],
}

# Magic bytes for audio file validation (first few bytes of file)
# Used for content-based MIME type verification
AUDIO_FILE_SIGNATURES = {
    b"ID3": "audio/mpeg",           # MP3 with ID3 tag
    b"\xff\xfb": "audio/mpeg",      # MP3 frame sync
    b"\xff\xfa": "audio/mpeg",      # MP3 frame sync
    b"\xff\xf3": "audio/mpeg",      # MP3 frame sync
    b"\xff\xf2": "audio/mpeg",      # MP3 frame sync
    b"RIFF": "audio/wav",           # WAV file
    b"ftyp": "audio/mp4",           # M4A/MP4 container (at offset 4)
    b"\x00\x00\x00": "audio/mp4",   # M4A/MP4 (ftyp at offset 4)
}

# =============================================================================
# Chat and Conversation
# =============================================================================

# Maximum number of messages in conversation history
MAX_CONVERSATION_HISTORY = int(os.environ.get("MAX_CONVERSATION_HISTORY", "20"))

# Maximum length of a single chat message
MAX_CHAT_MESSAGE_LENGTH = int(os.environ.get("MAX_CHAT_MESSAGE_LENGTH", "2000"))

# =============================================================================
# User and Session
# =============================================================================

# Anonymous user ID for standalone songwriter app (no auth system)
# This is used for audit/tracking purposes only
# In production, this should be replaced with actual user authentication
ANONYMOUS_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


def get_user_id(request_user_id: UUID | None = None) -> UUID:
    """
    Get the user ID for a request.

    If authentication is implemented, this can be extended to
    extract user ID from request context or JWT token.

    Args:
        request_user_id: Optional user ID from request context

    Returns:
        User ID to use for the request
    """
    return request_user_id or ANONYMOUS_USER_ID

# =============================================================================
# Pagination Defaults
# =============================================================================

# Default page size for list endpoints
DEFAULT_PAGE_SIZE = int(os.environ.get("DEFAULT_PAGE_SIZE", "50"))
MAX_PAGE_SIZE = int(os.environ.get("MAX_PAGE_SIZE", "100"))

# =============================================================================
# Analysis and Processing
# =============================================================================

# Timeout for LLM requests in seconds
LLM_REQUEST_TIMEOUT_SECONDS = int(os.environ.get("LLM_REQUEST_TIMEOUT_SECONDS", "120"))

# Timeout for audio analysis in seconds
AUDIO_ANALYSIS_TIMEOUT_SECONDS = int(os.environ.get("AUDIO_ANALYSIS_TIMEOUT_SECONDS", "300"))
