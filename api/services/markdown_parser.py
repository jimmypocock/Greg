"""
Markdown parser for song files.

Parses markdown files into Song objects:
- # Title -> song title
- ## Section Name -> section type (verse, chorus, bridge, etc.)
- Lines under sections -> lyrics
"""

import re
from typing import Optional

from api.enums import SectionType, SongStatus
from api.models import Line, Song, SongSection


def parse_section_header(header: str) -> tuple[SectionType, Optional[int]]:
    """
    Parse a section header like 'Verse', 'Verse 2', 'Chorus', etc.

    Returns (section_type, number or None)
    """
    header = header.strip().lower()

    # Extract number if present
    number_match = re.search(r'\d+', header)
    number = int(number_match.group()) if number_match else None

    # Remove number for type matching
    type_text = re.sub(r'\d+', '', header).strip()

    type_mapping = {
        'verse': SectionType.VERSE,
        'chorus': SectionType.CHORUS,
        'bridge': SectionType.BRIDGE,
        'pre-chorus': SectionType.PRE_CHORUS,
        'prechorus': SectionType.PRE_CHORUS,
        'pre chorus': SectionType.PRE_CHORUS,
        'post-chorus': SectionType.POST_CHORUS,
        'postchorus': SectionType.POST_CHORUS,
        'post chorus': SectionType.POST_CHORUS,
        'intro': SectionType.INTRO,
        'outro': SectionType.OUTRO,
        'instrumental': SectionType.INSTRUMENTAL,
        'solo': SectionType.SOLO,
        'breakdown': SectionType.BREAKDOWN,
        'line': SectionType.OTHER,  # Single line transitions
        'hook': SectionType.CHORUS,  # Treat hook as chorus
        'refrain': SectionType.CHORUS,
    }

    section_type = type_mapping.get(type_text, SectionType.OTHER)

    return section_type, number


def parse_markdown(content: str) -> Song:
    """
    Parse markdown content into a Song object.

    Format:
        # Song Title

        ## Verse
        First line of verse
        Second line of verse

        ## Chorus
        Chorus lyrics here

    If no ## headers are found, all content after # title becomes raw_input
    for AI structuring.
    """
    lines = content.strip().split('\n')

    title = "Untitled"
    raw_input_lines = []
    sections: list[SongSection] = []
    current_section_type: Optional[SectionType] = None
    current_section_number: Optional[int] = None
    current_lines: list[str] = []
    has_section_headers = False

    for line in lines:
        stripped = line.strip()

        # Title (# Header)
        if stripped.startswith('# ') and not stripped.startswith('## '):
            title = stripped[2:].strip()
            continue

        # Section header (## Header)
        if stripped.startswith('## '):
            has_section_headers = True

            # Save previous section
            if current_section_type is not None and current_lines:
                section = SongSection(
                    type=current_section_type,
                    number=current_section_number,
                    order=len(sections),
                    lines=[
                        Line(text=l, order=i)
                        for i, l in enumerate(current_lines) if l
                    ],
                )
                sections.append(section)
                current_lines = []

            # Parse new section
            header_text = stripped[3:].strip()
            current_section_type, current_section_number = parse_section_header(header_text)
            continue

        # Regular line
        if has_section_headers and current_section_type is not None:
            # Add to current section (keep empty lines for spacing awareness)
            if stripped:  # Only add non-empty lines
                current_lines.append(stripped)
        else:
            # No section headers yet, collect as raw input
            raw_input_lines.append(line)

    # Don't forget the last section
    if current_section_type is not None and current_lines:
        section = SongSection(
            type=current_section_type,
            number=current_section_number,
            order=len(sections),
            lines=[
                Line(text=l, order=i)
                for i, l in enumerate(current_lines) if l
            ],
        )
        sections.append(section)

    # Build raw_input from everything after title
    raw_input = '\n'.join(raw_input_lines).strip()
    if not raw_input and sections:
        # If we have sections, reconstruct raw_input from them for reference
        raw_parts = []
        for section in sections:
            for line in section.lines:
                raw_parts.append(line.text)
            raw_parts.append('')  # Blank line between sections
        raw_input = '\n'.join(raw_parts).strip()

    # Determine status
    status = SongStatus.DRAFT if sections else SongStatus.IDEA

    return Song(
        title=title,
        raw_input=raw_input,
        sections=sections,
        status=status,
    )


def parse_markdown_file(file_path: str) -> Song:
    """Parse a markdown file into a Song object."""
    with open(file_path, 'r') as f:
        content = f.read()
    return parse_markdown(content)
