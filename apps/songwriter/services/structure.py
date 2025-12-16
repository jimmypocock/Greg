"""
Structure suggestion service.

Uses LLM to analyze raw lyrics and suggest song structure.
"""

import json
import logging
from typing import Optional

from apps.songwriter.enums import SectionType
from apps.songwriter.models import (
    LineRequest,
    Section,
    StructureSuggestion,
)
from packages.core.llm import BaseLLMProvider, get_provider

logger = logging.getLogger(__name__)


STRUCTURE_PROMPT = '''You are an expert songwriter and music analyst. Analyze the following raw lyrics/text and identify the song structure.

For each section, determine:
1. The type (verse, chorus, pre-chorus, bridge, intro, outro, instrumental, solo, breakdown, other)
2. The section number if applicable (verse 1, verse 2, etc.)
3. Which lines belong to that section

Common patterns to look for:
- Repeated sections are usually choruses
- First unique section is usually verse 1
- Short sections before chorus are often pre-chorus
- Sections with different emotional tone/perspective are often bridges
- Look for natural breaks in theme or rhythm

RAW LYRICS:
{lyrics}

Respond with valid JSON in this exact format:
{{
    "sections": [
        {{
            "type": "verse",
            "number": 1,
            "lines": ["line 1 text", "line 2 text"]
        }},
        {{
            "type": "chorus",
            "number": null,
            "lines": ["chorus line 1", "chorus line 2"]
        }}
    ],
    "confidence": 0.85,
    "reasoning": "Brief explanation of why you structured it this way"
}}

Important:
- Use lowercase for section types: verse, chorus, pre-chorus, bridge, intro, outro, instrumental, solo, breakdown, other
- Keep the exact line text from the input
- Set number to null for sections that don't need numbering (like bridge, outro)
- Confidence should be 0.0-1.0 based on how clear the structure is'''


class StructureService:
    """Service for analyzing and suggesting song structure."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm_provider = llm_provider

    def _get_llm(self) -> BaseLLMProvider:
        """Get or create LLM provider."""
        if self.llm_provider is None:
            self.llm_provider = get_provider()
        return self.llm_provider

    async def suggest_structure(self, raw_lyrics: str) -> StructureSuggestion:
        """
        Analyze raw lyrics and suggest a song structure.

        Args:
            raw_lyrics: Unstructured lyrics text

        Returns:
            StructureSuggestion with sections and confidence
        """
        llm = self._get_llm()

        prompt = STRUCTURE_PROMPT.format(lyrics=raw_lyrics)

        try:
            # Get LLM response
            response_text = ""
            for chunk in llm.generate_stream(
                prompt=prompt,
                system_prompt="You are a helpful songwriting assistant. Always respond with valid JSON.",
            ):
                response_text += chunk

            # Parse JSON response
            response_data = json.loads(response_text)

            # Convert to our models
            sections = []
            for section_data in response_data.get("sections", []):
                # Map section type
                section_type_str = section_data.get("type", "other").lower().replace(" ", "-")
                try:
                    section_type = SectionType(section_type_str)
                except ValueError:
                    section_type = SectionType.OTHER

                # Create lines
                lines = [
                    LineRequest(text=line_text)
                    for line_text in section_data.get("lines", [])
                ]

                section = Section(
                    type=section_type,
                    number=section_data.get("number"),
                    lines=lines,
                )
                sections.append(section)

            return StructureSuggestion(
                sections=sections,
                confidence=response_data.get("confidence", 0.5),
                reasoning=response_data.get("reasoning"),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Return a basic fallback structure
            return self._fallback_structure(raw_lyrics)

        except Exception as e:
            logger.error(f"Error suggesting structure: {e}")
            return self._fallback_structure(raw_lyrics)

    def _fallback_structure(self, raw_lyrics: str) -> StructureSuggestion:
        """
        Create a basic fallback structure when AI fails.

        Puts everything in a single verse section.
        """
        lines = [
            LineRequest(text=line.strip())
            for line in raw_lyrics.strip().split("\n")
            if line.strip()
        ]

        return StructureSuggestion(
            sections=[
                Section(
                    type=SectionType.OTHER,
                    number=None,
                    lines=lines,
                    notes="Auto-generated fallback structure. Please review and reorganize.",
                )
            ],
            confidence=0.1,
            reasoning="Fallback structure - AI parsing failed. All lines placed in a single section for manual organization.",
        )

    def parse_existing_structure(self, raw_lyrics: str) -> list[Section]:
        """
        Parse lyrics that already have section markers like [Verse 1], [Chorus].

        This is a non-AI approach for when users paste pre-formatted lyrics.
        """
        sections = []
        current_section = None
        current_lines = []

        for line in raw_lyrics.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Check for section markers like [Verse 1] or [Chorus]
            if line.startswith("[") and line.endswith("]"):
                # Save previous section
                if current_section or current_lines:
                    sections.append(Section(
                        type=current_section or SectionType.OTHER,
                        number=self._extract_section_number(line),
                        lines=[LineRequest(text=l) for l in current_lines],
                    ))
                    current_lines = []

                # Parse new section
                section_text = line[1:-1].lower().strip()
                current_section = self._parse_section_type(section_text)
            else:
                current_lines.append(line)

        # Don't forget the last section
        if current_lines:
            sections.append(Section(
                type=current_section or SectionType.OTHER,
                lines=[LineRequest(text=l) for l in current_lines],
            ))

        return sections

    def _parse_section_type(self, text: str) -> SectionType:
        """Parse section type from text like 'verse 1' or 'chorus'."""
        text = text.lower().split()[0] if text.split() else "other"

        mapping = {
            "verse": SectionType.VERSE,
            "chorus": SectionType.CHORUS,
            "bridge": SectionType.BRIDGE,
            "pre-chorus": SectionType.PRE_CHORUS,
            "prechorus": SectionType.PRE_CHORUS,
            "post-chorus": SectionType.POST_CHORUS,
            "postchorus": SectionType.POST_CHORUS,
            "intro": SectionType.INTRO,
            "outro": SectionType.OUTRO,
            "instrumental": SectionType.INSTRUMENTAL,
            "solo": SectionType.SOLO,
            "breakdown": SectionType.BREAKDOWN,
        }
        return mapping.get(text, SectionType.OTHER)

    def _extract_section_number(self, marker: str) -> Optional[int]:
        """Extract section number from marker like '[Verse 2]'."""
        import re
        match = re.search(r'\d+', marker)
        return int(match.group()) if match else None


# Module-level instance
_structure_service: Optional[StructureService] = None


def get_structure_service() -> StructureService:
    """Get or create the structure service singleton."""
    global _structure_service
    if _structure_service is None:
        _structure_service = StructureService()
    return _structure_service
