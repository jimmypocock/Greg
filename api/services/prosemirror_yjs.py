"""
ProseMirror Yjs schema for collaborative song editing.

This module provides utilities for creating and manipulating Yjs documents
that are compatible with y-prosemirror on the frontend.

Schema:
  Y.XmlFragment('prosemirror') [
    Y.XmlElement('part', attrs: {id, type, mainVersionId}) [
      Y.XmlElement('label') [
        Y.XmlText('Verse 1')
      ]
      Y.XmlElement('line', attrs: {lineType}) [
        Y.XmlText('lyrics here...')
      ]
      ...more lines...
    ]
    ...more parts...
  ]
"""

import logging
from uuid import UUID, uuid4
from typing import Optional

from pycrdt import Doc, XmlFragment, XmlElement, XmlText

from api.enums import SectionType, LineType

logger = logging.getLogger(__name__)


def create_empty_prosemirror_doc(song_id: UUID, title: str = "Untitled") -> Doc:
    """
    Create an empty Yjs document for ProseMirror.

    Args:
        song_id: The song UUID
        title: Song title

    Returns:
        Yjs Doc with empty prosemirror XmlFragment
    """
    doc = Doc()

    with doc.transaction():
        # Create the prosemirror XmlFragment (root)
        fragment = doc.get('prosemirror', type=XmlFragment)

        # Create a default part with empty label
        part = XmlElement('part')
        fragment.children.append(part)

        part_id = str(uuid4())
        part.attributes['id'] = part_id
        part.attributes['type'] = SectionType.VERSE.value
        part.attributes['mainVersionId'] = ''

        # Add label
        label = XmlElement('label')
        part.children.append(label)
        label_text = XmlText()
        label.children.append(label_text)
        label_text += 'Verse 1'

        # Add empty first line
        line = XmlElement('line')
        part.children.append(line)
        line.attributes['lineType'] = LineType.LYRIC.value
        line_text = XmlText()
        line.children.append(line_text)

    return doc


def sql_song_to_prosemirror_doc(song) -> Doc:
    """
    Convert a SQL Song object to a ProseMirror-compatible Yjs document.

    Args:
        song: Song model with sections, versions, and lines loaded

    Returns:
        Yjs Doc with prosemirror XmlFragment structure
    """
    doc = Doc()

    with doc.transaction():
        fragment = doc.get('prosemirror', type=XmlFragment)

        for section in sorted(song.sections, key=lambda s: s.order):
            # Create part element
            part = XmlElement('part')
            fragment.children.append(part)

            part.attributes['id'] = str(section.id)
            part.attributes['type'] = section.type.value
            part.attributes['mainVersionId'] = str(section.main_version.id) if section.main_version else ''

            # Add label
            label = XmlElement('label')
            part.children.append(label)
            label_text = XmlText()
            label.children.append(label_text)
            label_text += section.display_label

            # Add lines from main version
            main_version = section.main_version
            if main_version:
                for line_model in sorted(main_version.lines, key=lambda l: l.order):
                    line = XmlElement('line')
                    part.children.append(line)
                    line.attributes['lineType'] = line_model.line_type.value if line_model.line_type else LineType.LYRIC.value

                    line_text = XmlText()
                    line.children.append(line_text)
                    line_text += line_model.text or ''

        # If no sections, create a default part
        if not song.sections:
            part = XmlElement('part')
            fragment.children.append(part)

            part_id = str(uuid4())
            part.attributes['id'] = part_id
            part.attributes['type'] = SectionType.VERSE.value
            part.attributes['mainVersionId'] = ''

            label = XmlElement('label')
            part.children.append(label)
            label_text = XmlText()
            label.children.append(label_text)
            label_text += 'Verse 1'

            line = XmlElement('line')
            part.children.append(line)
            line.attributes['lineType'] = LineType.LYRIC.value
            line_text = XmlText()
            line.children.append(line_text)

    logger.info(f"Converted song {song.id} to ProseMirror doc with {len(list(fragment.children))} parts")
    return doc


def add_part_to_doc(
    doc: Doc,
    part_type: SectionType = SectionType.VERSE,
    label_text: str = "New Part",
    after_part_id: Optional[UUID] = None,
) -> str:
    """
    Add a new part to the document.

    Args:
        doc: The Yjs document
        part_type: Type of part (verse, chorus, etc.)
        label_text: Display label for the part
        after_part_id: Insert after this part (or append if None)

    Returns:
        The new part's UUID string
    """
    fragment = doc.get('prosemirror', type=XmlFragment)
    part_id = str(uuid4())

    with doc.transaction():
        # Create part element
        part = XmlElement('part')

        # Find insertion position
        insert_index = len(list(fragment.children))
        if after_part_id:
            after_id_str = str(after_part_id)
            for i, child in enumerate(fragment.children):
                if child.attributes.get('id') == after_id_str:
                    insert_index = i + 1
                    break

        # Insert at position (or append)
        if insert_index >= len(list(fragment.children)):
            fragment.children.append(part)
        else:
            fragment.children.insert(insert_index, part)

        # Set attributes
        part.attributes['id'] = part_id
        part.attributes['type'] = part_type.value
        part.attributes['mainVersionId'] = ''

        # Add label
        label = XmlElement('label')
        part.children.append(label)
        label_elem_text = XmlText()
        label.children.append(label_elem_text)
        label_elem_text += label_text

        # Add empty first line
        line = XmlElement('line')
        part.children.append(line)
        line.attributes['lineType'] = LineType.LYRIC.value
        line_text = XmlText()
        line.children.append(line_text)

    logger.debug(f"Added part {part_id} with label '{label_text}'")
    return part_id


def get_part_by_id(doc: Doc, part_id: UUID) -> Optional[XmlElement]:
    """Find a part in the document by ID."""
    fragment = doc.get('prosemirror', type=XmlFragment)
    part_id_str = str(part_id)

    for child in fragment.children:
        if hasattr(child, 'attributes') and child.attributes.get('id') == part_id_str:
            return child

    return None


def delete_part_from_doc(doc: Doc, part_id: UUID) -> bool:
    """
    Delete a part from the document.

    Returns:
        True if part was found and deleted
    """
    fragment = doc.get('prosemirror', type=XmlFragment)
    part_id_str = str(part_id)

    with doc.transaction():
        for i, child in enumerate(fragment.children):
            if hasattr(child, 'attributes') and child.attributes.get('id') == part_id_str:
                del fragment.children[i]
                logger.debug(f"Deleted part {part_id}")
                return True

    return False


def update_part_label(doc: Doc, part_id: UUID, new_label: str) -> bool:
    """
    Update a part's label text.

    Returns:
        True if part was found and updated
    """
    part = get_part_by_id(doc, part_id)
    if not part:
        return False

    with doc.transaction():
        # Find the label element (first child with tag 'label')
        for child in part.children:
            if hasattr(child, 'tag') and child.tag == 'label':
                # Clear existing text and add new
                for text_child in child.children:
                    if isinstance(text_child, XmlText):
                        # Delete existing content
                        text_child.clear()
                        text_child += new_label
                        logger.debug(f"Updated part {part_id} label to '{new_label}'")
                        return True

    return False


def add_line_to_part(
    doc: Doc,
    part_id: UUID,
    text: str = "",
    line_type: LineType = LineType.LYRIC,
    after_line_index: Optional[int] = None,
) -> bool:
    """
    Add a new line to a part.

    Args:
        doc: The Yjs document
        part_id: The part to add line to
        text: Line text content
        line_type: Type of line (lyric, chord, annotation)
        after_line_index: Insert after this line index (0-based, excluding label)

    Returns:
        True if line was added
    """
    part = get_part_by_id(doc, part_id)
    if not part:
        return False

    with doc.transaction():
        line = XmlElement('line')

        # Calculate insertion position (skip label at index 0)
        # Lines start at index 1
        if after_line_index is not None:
            insert_pos = after_line_index + 2  # +1 for label, +1 for after
        else:
            insert_pos = len(list(part.children))

        if insert_pos >= len(list(part.children)):
            part.children.append(line)
        else:
            part.children.insert(insert_pos, line)

        line.attributes['lineType'] = line_type.value
        line_text = XmlText()
        line.children.append(line_text)
        line_text += text

    return True


def doc_to_json(doc: Doc) -> dict:
    """
    Convert a ProseMirror Yjs document to JSON format.

    This produces a structure compatible with ProseMirror's JSON format.
    """
    fragment = doc.get('prosemirror', type=XmlFragment)

    content = []
    for part in fragment.children:
        if not hasattr(part, 'tag') or part.tag != 'part':
            continue

        part_content = []

        for child in part.children:
            if not hasattr(child, 'tag'):
                continue

            if child.tag == 'label':
                # Extract label text
                label_text = ''
                for text_node in child.children:
                    label_text += str(text_node)

                part_content.append({
                    'type': 'label',
                    'content': [{'type': 'text', 'text': label_text}] if label_text else []
                })

            elif child.tag == 'line':
                # Extract line text
                line_text = ''
                for text_node in child.children:
                    line_text += str(text_node)

                part_content.append({
                    'type': 'line',
                    'attrs': {
                        'lineType': child.attributes.get('lineType')
                    },
                    'content': [{'type': 'text', 'text': line_text}] if line_text else []
                })

        content.append({
            'type': 'part',
            'attrs': {
                'id': part.attributes.get('id'),
                'type': part.attributes.get('type'),
                'mainVersionId': part.attributes.get('mainVersionId'),
            },
            'content': part_content
        })

    return {
        'type': 'doc',
        'content': content
    }
