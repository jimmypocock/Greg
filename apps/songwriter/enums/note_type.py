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
