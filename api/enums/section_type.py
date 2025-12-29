"""Section type enum."""

from enum import Enum


class SectionType(str, Enum):
    """Types of song sections."""

    INTRO = "INTRO"
    VERSE = "VERSE"
    PRE_CHORUS = "PRE_CHORUS"
    CHORUS = "CHORUS"
    POST_CHORUS = "POST_CHORUS"
    BRIDGE = "BRIDGE"
    OUTRO = "OUTRO"
    INSTRUMENTAL = "INSTRUMENTAL"
    SOLO = "SOLO"
    BREAKDOWN = "BREAKDOWN"
    BRAIN_DUMP = "BRAIN_DUMP"
    OTHER = "OTHER"
