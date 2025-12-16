"""Agent type enum."""

from enum import Enum


class AgentType(str, Enum):
    """Types of AI agents available."""

    CRITIC = "critic"
    LYRICIST = "lyricist"
    STRUCTURE = "structure"
    MELODY = "melody"
