"""
Yjs document schema for songs.

Provides helpers for creating and manipulating Yjs documents
that represent song structure.

Schema:
  Y.Doc {
    'meta': Y.Map {
      'id': str (song UUID)
      'title': str
      'key': str | None
      'tempo': int | None
      'time_signature': str
      'status': str
    }
    'canvas': Y.Text
      Raw text content for the canvas editor.
      Format:
        # Section Type
        Lyric line
        > Chord line
        // Annotation
    'sections': Y.Array<Y.Map> [
      Y.Map {
        'id': str (section UUID)
        'type': str (SectionType value)
        'number': int | None
        'main_version_id': str (version UUID)
        'lines': Y.Array<Y.Map> [
          Y.Map {
            'id': str (line UUID)
            'text': str (line text)
            'line_type': str (LineType value)
            'chords': Y.Array<Y.Map> [
              Y.Map { 'chord': str, 'position': int }
            ]
          }
        ]
      }
    ]
  }
"""

import logging
from uuid import UUID, uuid4

from pycrdt import Doc, Array, Map, Text

from api.enums import SectionType, LineType

logger = logging.getLogger(__name__)


def song_to_canvas_text(song) -> str:
    """
    Convert a SQL Song object to canvas text format.

    Format:
      # Section Type
      Lyric line
      > Chord line (chords joined by space)
      // Annotation

    Args:
        song: Song model with sections, versions, and lines loaded

    Returns:
        Text representation for the canvas editor
    """
    lines = []

    for section in sorted(song.sections, key=lambda s: s.order):
        # Section header
        section_type = section.type.value.replace("_", " ").title()
        if section.number:
            section_type = f"{section_type} {section.number}"
        lines.append(f"# {section_type}")

        # Get main version lines
        main_version = section.main_version
        if main_version:
            for line in sorted(main_version.lines, key=lambda l: l.order):
                if line.line_type and line.line_type.value == "CHORD":
                    # Chord line
                    lines.append(f"> {line.text or ''}")
                elif line.line_type and line.line_type.value == "ANNOTATION":
                    # Annotation
                    lines.append(f"// {line.text or ''}")
                else:
                    # Regular lyric line
                    lines.append(line.text or "")

        # Add blank line after section
        lines.append("")

    return "\n".join(lines).strip()


def create_empty_yjs_doc(song_id: UUID, title: str = "Untitled") -> Doc:
    """Create an empty Yjs document for a new song."""
    doc = Doc()

    # Initialize meta - must integrate into doc BEFORE setting values
    doc["meta"] = meta = Map()
    meta["id"] = str(song_id)
    meta["title"] = title
    meta["key"] = None
    meta["tempo"] = None
    meta["time_signature"] = "4/4"
    meta["status"] = "IDEA"

    # Initialize canvas text (empty) - use doc.get() for proper integration
    doc.get("canvas", type=Text)

    # Initialize empty sections array
    doc["sections"] = Array()

    return doc


def sql_song_to_yjs(song) -> Doc:
    """
    Convert a SQL Song object to a Yjs document.

    Args:
        song: Song model with sections, versions, and lines loaded

    Returns:
        Yjs Doc populated with song data
    """
    doc = Doc()

    # Set meta - must integrate into doc BEFORE setting values
    doc["meta"] = meta = Map()
    meta["id"] = str(song.id)
    meta["title"] = song.title or "Untitled"
    meta["key"] = song.key
    meta["tempo"] = song.tempo
    meta["time_signature"] = song.time_signature or "4/4"
    meta["status"] = song.status.value if song.status else "IDEA"

    # Set canvas text - use doc.get() to properly integrate the Text type
    # This is the correct pycrdt pattern for creating shared types
    canvas_text = song_to_canvas_text(song)
    with doc.transaction():
        canvas = doc.get("canvas", type=Text)
        if canvas_text:
            canvas += canvas_text

    logger.info(f"Created Yjs doc with canvas: {len(canvas_text)} chars")

    # Set sections - integrate into doc first
    doc["sections"] = sections_array = Array()

    for section in sorted(song.sections, key=lambda s: s.order):
        # Create section map and append to array (integrating it)
        section_map = Map()
        sections_array.append(section_map)

        # Now we can set values
        section_map["id"] = str(section.id)
        section_map["type"] = section.type.value
        section_map["number"] = section.number

        # Get main version
        main_version = section.main_version
        section_map["main_version_id"] = str(main_version.id) if main_version else None

        # Add lines array to section (integrating it)
        section_map["lines"] = lines_array = Array()

        if main_version:
            for line in sorted(main_version.lines, key=lambda l: l.order):
                # Create line map and append to array (integrating it)
                line_map = Map()
                lines_array.append(line_map)

                # Now set values
                line_map["id"] = str(line.id)
                line_map["text"] = line.text or ""
                line_map["line_type"] = line.line_type.value if line.line_type else "LYRIC"

                # Add chords array to line (integrating it)
                line_map["chords"] = chords_array = Array()

                for chord in sorted(line.chords, key=lambda c: c.position):
                    chord_map = Map()
                    chords_array.append(chord_map)
                    chord_map["chord"] = chord.chord
                    chord_map["position"] = chord.position

    logger.debug(f"Converted song {song.id} to Yjs doc with {len(sections_array)} sections")
    return doc


def get_section_by_id(doc: Doc, section_id: UUID) -> Map | None:
    """Find a section in the Yjs doc by ID."""
    sections = doc["sections"] if "sections" in doc else None
    if not sections:
        return None

    section_id_str = str(section_id)
    for section in sections:
        if section.get("id") == section_id_str:
            return section
    return None


def get_line_by_id(doc: Doc, section_id: UUID, line_id: UUID) -> Map | None:
    """Find a line in a section by ID."""
    section = get_section_by_id(doc, section_id)
    if not section:
        return None

    lines = section.get("lines")
    if not lines:
        return None

    line_id_str = str(line_id)
    for line in lines:
        if line.get("id") == line_id_str:
            return line
    return None


def add_section_to_yjs(
    doc: Doc,
    section_type: SectionType,
    number: int | None = None,
    after_section_id: UUID | None = None,
) -> tuple[UUID, UUID]:
    """
    Add a new section to Yjs document.

    Args:
        doc: The Yjs document
        section_type: Type of section (VERSE, CHORUS, etc.)
        number: Optional section number
        after_section_id: Insert after this section (or append if None)

    Returns:
        Tuple of (section_id, version_id)
    """
    section_id = uuid4()
    version_id = uuid4()

    sections_array = doc["sections"] if "sections" in doc else None
    if sections_array is None:
        doc["sections"] = sections_array = Array()

    # Create and integrate section_map first, then set values
    section_map = Map()

    if after_section_id:
        after_id_str = str(after_section_id)
        for i, s in enumerate(sections_array):
            if s.get("id") == after_id_str:
                sections_array.insert(i + 1, section_map)
                # Now set values after integration
                section_map["id"] = str(section_id)
                section_map["type"] = section_type.value
                section_map["number"] = number
                section_map["main_version_id"] = str(version_id)
                section_map["lines"] = Array()
                logger.debug(f"Inserted section {section_id} after {after_section_id}")
                return section_id, version_id

    # Append at end
    sections_array.append(section_map)
    # Now set values after integration
    section_map["id"] = str(section_id)
    section_map["type"] = section_type.value
    section_map["number"] = number
    section_map["main_version_id"] = str(version_id)
    section_map["lines"] = Array()
    logger.debug(f"Appended section {section_id}")
    return section_id, version_id


def add_line_to_yjs(
    doc: Doc,
    section_id: UUID,
    text: str = "",
    line_type: LineType = LineType.LYRIC,
    after_line_id: UUID | None = None,
) -> UUID:
    """
    Add a new line to a section.

    Args:
        doc: The Yjs document
        section_id: Section to add line to
        text: Line text
        line_type: Type of line
        after_line_id: Insert after this line (or append if None)

    Returns:
        The new line ID

    Raises:
        ValueError: If section not found
    """
    line_id = uuid4()

    section = get_section_by_id(doc, section_id)
    if not section:
        raise ValueError(f"Section {section_id} not found")

    lines_array = section.get("lines")
    if lines_array is None:
        section["lines"] = lines_array = Array()

    # Create line_map and integrate first, then set values
    line_map = Map()

    if after_line_id:
        after_id_str = str(after_line_id)
        for i, line in enumerate(lines_array):
            if line.get("id") == after_id_str:
                lines_array.insert(i + 1, line_map)
                # Set values after integration
                line_map["id"] = str(line_id)
                line_map["text"] = text
                line_map["line_type"] = line_type.value
                line_map["chords"] = Array()
                logger.debug(f"Inserted line {line_id} after {after_line_id}")
                return line_id

    # Append at end
    lines_array.append(line_map)
    # Set values after integration
    line_map["id"] = str(line_id)
    line_map["text"] = text
    line_map["line_type"] = line_type.value
    line_map["chords"] = Array()
    logger.debug(f"Appended line {line_id} to section {section_id}")
    return line_id


def delete_section_from_yjs(doc: Doc, section_id: UUID) -> bool:
    """
    Delete a section from the Yjs document.

    Returns:
        True if section was found and deleted
    """
    sections_array = doc["sections"] if "sections" in doc else None
    if not sections_array:
        return False

    section_id_str = str(section_id)
    for i, section in enumerate(sections_array):
        if section.get("id") == section_id_str:
            del sections_array[i]
            logger.debug(f"Deleted section {section_id}")
            return True

    return False


def delete_line_from_yjs(doc: Doc, section_id: UUID, line_id: UUID) -> bool:
    """
    Delete a line from a section.

    Returns:
        True if line was found and deleted
    """
    section = get_section_by_id(doc, section_id)
    if not section:
        return False

    lines_array = section.get("lines")
    if not lines_array:
        return False

    line_id_str = str(line_id)
    for i, line in enumerate(lines_array):
        if line.get("id") == line_id_str:
            del lines_array[i]
            logger.debug(f"Deleted line {line_id} from section {section_id}")
            return True

    return False


def update_line_text(doc: Doc, section_id: UUID, line_id: UUID, text: str) -> bool:
    """
    Update a line's text.

    Returns:
        True if line was found and updated
    """
    line = get_line_by_id(doc, section_id, line_id)
    if not line:
        return False

    line["text"] = text
    return True


def update_line_type(doc: Doc, section_id: UUID, line_id: UUID, line_type: LineType) -> bool:
    """
    Update a line's type.

    Returns:
        True if line was found and updated
    """
    line = get_line_by_id(doc, section_id, line_id)
    if not line:
        return False

    line["line_type"] = line_type.value
    return True


def add_chord_to_line(
    doc: Doc,
    section_id: UUID,
    line_id: UUID,
    chord: str,
    position: int,
) -> bool:
    """
    Add a chord to a line.

    Returns:
        True if chord was added
    """
    line = get_line_by_id(doc, section_id, line_id)
    if not line:
        return False

    chords_array = line.get("chords")
    if chords_array is None:
        line["chords"] = chords_array = Array()

    # Integrate chord_map first, then set values
    chord_map = Map()
    chords_array.append(chord_map)
    chord_map["chord"] = chord
    chord_map["position"] = position

    logger.debug(f"Added chord {chord} at position {position} to line {line_id}")
    return True


def remove_chord_from_line(
    doc: Doc,
    section_id: UUID,
    line_id: UUID,
    position: int,
) -> bool:
    """
    Remove a chord from a line by position.

    Returns:
        True if chord was found and removed
    """
    line = get_line_by_id(doc, section_id, line_id)
    if not line:
        return False

    chords_array = line.get("chords")
    if not chords_array:
        return False

    for i, chord in enumerate(chords_array):
        if chord.get("position") == position:
            del chords_array[i]
            logger.debug(f"Removed chord at position {position} from line {line_id}")
            return True

    return False
