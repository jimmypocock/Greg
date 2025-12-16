"""Song status enum."""

from enum import Enum


class SongStatus(str, Enum):
    """Status of a song in the writing process."""

    IDEA = "idea"
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    FINISHED = "finished"
