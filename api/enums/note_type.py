"""Note type enum for categorizing song notes."""

from enum import Enum


class NoteType(str, Enum):
    """Types of notes that can be attached to songs."""

    IDEA = "IDEA"  # Random ideas, what-ifs
    INSPIRATION = "INSPIRATION"  # What inspired this song
    REFERENCE = "REFERENCE"  # Songs/artists to reference
    CONTEXT = "CONTEXT"  # Background info (who it's for, occasion)
    TODO = "TODO"  # Things to work on
    FEEDBACK = "FEEDBACK"  # Feedback from others
    OTHER = "OTHER"  # Anything else
    SONG_SHAPE = "SONG_SHAPE"  # Structured shape data from exploration session (deprecated)

    # Shape exploration data (stored as individual notes for visibility)
    THEME = "THEME"  # The song's core theme/concept
    KEY_IMAGE = "KEY_IMAGE"  # Key images, phrases, or metaphors
    EMOTIONAL_ARC = "EMOTIONAL_ARC"  # The emotional journey (start → turning point → end)
    FRAGMENT = "FRAGMENT"  # User's raw lyric fragments
