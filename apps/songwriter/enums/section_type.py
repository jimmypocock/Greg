"""Section type enum."""

from enum import Enum


class SectionType(str, Enum):
    """Types of song sections."""

    INTRO = "intro"
    VERSE = "verse"
    PRE_CHORUS = "pre-chorus"
    CHORUS = "chorus"
    POST_CHORUS = "post-chorus"
    BRIDGE = "bridge"
    OUTRO = "outro"
    INSTRUMENTAL = "instrumental"
    SOLO = "solo"
    BREAKDOWN = "breakdown"
    BRAIN_DUMP = "brain-dump"  # Unstructured content for brainstorming
    OTHER = "other"
