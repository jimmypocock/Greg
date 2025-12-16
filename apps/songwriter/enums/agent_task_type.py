"""Agent task type enum."""

from enum import Enum


class AgentTaskType(str, Enum):
    """Types of tasks agents can perform."""

    # Critic tasks
    FULL_REVIEW = "full_review"
    SECTION_REVIEW = "section_review"
    CHECK_CLICHES = "check_cliches"
    ANALYZE_RHYTHM = "analyze_rhythm"

    # Structure tasks
    STRUCTURE_ANALYSIS = "structure_analysis"

    # Lyricist tasks (future)
    WRITE_SECTION = "write_section"
    SUGGEST_LYRICS = "suggest_lyrics"

    # Melody tasks (future)
    SUGGEST_CHORDS = "suggest_chords"
