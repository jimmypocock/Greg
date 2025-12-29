"""Song status enum."""

from enum import Enum


class SongStatus(str, Enum):
    """Status of a song in the writing process."""

    IDEA = "IDEA"
    DRAFT = "DRAFT"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW = "REVIEW"
    FINISHED = "FINISHED"
