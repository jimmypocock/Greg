"""Agent type enum."""

from enum import Enum


class AgentType(str, Enum):
    """Types of AI agents available."""

    CRITIC = "CRITIC"
    LYRICIST = "LYRICIST"
    STRUCTURE = "STRUCTURE"
    MELODY = "MELODY"
    ORCHESTRATOR = "ORCHESTRATOR"
    SONG_SHAPER = "SONG_SHAPER"
