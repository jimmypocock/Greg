"""Agent task type enum."""

from enum import Enum


class AgentTaskType(str, Enum):
    """Types of tasks agents can perform."""

    # Critic tasks
    FULL_REVIEW = "FULL_REVIEW"
    SECTION_REVIEW = "SECTION_REVIEW"
    CHECK_CLICHES = "CHECK_CLICHES"
    ANALYZE_RHYTHM = "ANALYZE_RHYTHM"

    # Structure tasks
    STRUCTURE_ANALYSIS = "STRUCTURE_ANALYSIS"

    # Orchestrator tasks (conversational chat)
    CHAT = "CHAT"

    # Lyricist tasks (future)
    WRITE_SECTION = "WRITE_SECTION"
    SUGGEST_LYRICS = "SUGGEST_LYRICS"

    # Melody tasks (future)
    SUGGEST_CHORDS = "SUGGEST_CHORDS"

    # Song shaper tasks (new song exploration)
    SHAPE_EXPLORATION = "SHAPE_EXPLORATION"
