"""
In-memory song store.

DEPRECATED: This module is no longer used in production.
Use SongDBStore for database-backed storage instead.

This file is kept for reference only and may be removed in a future version.
"""

import warnings
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from apps.songwriter.models import Song

warnings.warn(
    "SongStore (in-memory store) is deprecated. Use SongDBStore instead.",
    DeprecationWarning,
    stacklevel=2,
)


def utc_now() -> datetime:
    """Get current UTC time (Python 3.12+ compatible)."""
    return datetime.now(timezone.utc)


class SongStore:
    """In-memory storage for songs."""

    def __init__(self):
        self._songs: dict[UUID, Song] = {}

    def create(self, song: Song) -> Song:
        """Store a new song."""
        self._songs[song.id] = song
        return song

    def get(self, song_id: UUID) -> Optional[Song]:
        """Get a song by ID."""
        return self._songs.get(song_id)

    def list_all(self) -> list[Song]:
        """List all songs, sorted by updated_at descending."""
        return sorted(
            self._songs.values(),
            key=lambda s: s.updated_at,
            reverse=True,
        )

    def update(self, song_id: UUID, song: Song) -> Optional[Song]:
        """Update an existing song."""
        if song_id not in self._songs:
            return None
        song.updated_at = utc_now()
        self._songs[song_id] = song
        return song

    def delete(self, song_id: UUID) -> bool:
        """Delete a song. Returns True if deleted, False if not found."""
        if song_id in self._songs:
            del self._songs[song_id]
            return True
        return False

    def clear(self) -> int:
        """Clear all songs. Returns count of deleted songs."""
        count = len(self._songs)
        self._songs.clear()
        return count


# Global instance
song_store = SongStore()


def get_song_store() -> SongStore:
    """Get the song store instance."""
    return song_store
