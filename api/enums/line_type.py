"""Line type enum for canvas-based song editing."""

from enum import Enum


class LineType(str, Enum):
    """Types of lines in a song document."""

    LYRIC = "LYRIC"
    CHORD = "CHORD"
    SECTION_HEADER = "SECTION_HEADER"
    ANNOTATION = "ANNOTATION"
