"""
Critic agent using PydanticAI.

This agent provides constructive feedback on songs, analyzing lyrics for
clichés, rhythm, structure, and overall quality.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from api.database.models import Song
from api.agents.tools import (
    detect_cliches,
    count_syllables,
    get_song_lyrics,
    get_song_sections,
    get_song_metadata,
    get_song_summary,
)


# Agent dependencies - injected at runtime
@dataclass
class CriticDependencies:
    """Dependencies for the Critic agent."""
    song: Song


# Structured output for reviews
class SongReview(BaseModel):
    """Structured output from a song review."""
    overall_impression: str
    strengths: list[str]
    areas_for_improvement: list[str]
    specific_suggestions: list[str]
    cliche_analysis: str | None = None
    rhythm_analysis: str | None = None


# System prompt for the critic agent
CRITIC_SYSTEM_PROMPT = """You are a Constructive Music Critic - a respected A&R executive and former music journalist who has developed hundreds of artists from raw talent to chart-topping success.

You have exceptionally high standards but have learned that the best feedback inspires improvement rather than discouragement. You can identify exactly what's not working in a song and articulate why, while also recognizing and celebrating what IS working.

You understand commercial appeal but also value artistic integrity.

When reviewing songs:
1. Start by understanding the full context using the available tools
2. Identify both strengths and weaknesses
3. Provide specific, actionable feedback
4. Be encouraging but honest
5. Suggest concrete improvements, not vague advice

Available tools:
- get_lyrics: Get the full lyrics of the song
- get_sections: Get information about song sections
- get_metadata: Get song metadata (key, tempo, etc.)
- get_summary: Get a quick summary of the song
- detect_cliches: Scan lyrics for overused phrases
- count_syllables: Analyze rhythm and meter"""


# Create the critic agent
critic_agent = Agent(
    "openai:gpt-4o-mini",  # Default model, can be overridden
    deps_type=CriticDependencies,
    system_prompt=CRITIC_SYSTEM_PROMPT,
)


# Register tools with the agent
@critic_agent.tool
def get_lyrics(ctx: RunContext[CriticDependencies]) -> str:
    """Get the full lyrics of the current song."""
    return get_song_lyrics(ctx.deps.song)


@critic_agent.tool
def get_sections(ctx: RunContext[CriticDependencies]) -> str:
    """Get information about the song's sections."""
    return get_song_sections(ctx.deps.song)


@critic_agent.tool
def get_metadata(ctx: RunContext[CriticDependencies]) -> str:
    """Get metadata about the current song."""
    return get_song_metadata(ctx.deps.song)


@critic_agent.tool
def get_summary(ctx: RunContext[CriticDependencies]) -> str:
    """Get a summary of the current song."""
    return get_song_summary(ctx.deps.song)


@critic_agent.tool_plain
def scan_for_cliches(text: str) -> str:
    """Scan lyrics for common songwriting clichés and overused phrases."""
    return detect_cliches(text)


@critic_agent.tool_plain
def analyze_syllables(text: str) -> str:
    """Count syllables in lyrics to check meter and rhythm."""
    return count_syllables(text)


# Task prompts for different review types
FULL_REVIEW_PROMPT = """Perform a comprehensive review of the song "{title}".

First, use the tools to gather information:
1. Get the full lyrics
2. Get the sections structure
3. Scan for clichés
4. Analyze the syllable patterns

Then provide feedback on:
1. **Overall Impression**: What's working well? What's the song's strongest element?
2. **Lyrics Analysis**: Are the lyrics original? Do they convey emotion effectively?
3. **Structure**: Does the song flow well? Are sections balanced?
4. **Rhythm & Meter**: Is the syllable count consistent within sections?
5. **Clichés**: Any overused phrases that should be refreshed?
6. **Specific Suggestions**: 3-5 concrete, actionable improvements

Be constructive and specific. Don't just say "improve the chorus" - suggest HOW."""


CLICHE_CHECK_PROMPT = """Scan the song "{title}" for clichés and overused phrases.

Use the tools to:
1. Get the full lyrics
2. Run the cliché detector

For each cliché found, suggest 2-3 fresh alternatives that maintain the same meaning.
If no clichés are found, acknowledge the originality of the lyrics."""


RHYTHM_ANALYSIS_PROMPT = """Analyze the rhythm and meter of the song "{title}".

Use the tools to:
1. Get the song sections
2. Get the full lyrics
3. Count syllables for each section

Analyze:
1. Syllable consistency within verses (do all verses have similar patterns?)
2. Syllable consistency within choruses
3. Overall rhythmic flow - does it feel singable?
4. Any lines that feel awkward or don't fit the established pattern

Suggest specific rewrites for any rhythmically awkward lines."""


SECTION_REVIEW_PROMPT = """Review the {section_type} section of "{title}".

Section lyrics:
{section_lyrics}

Use the tools to:
1. Get context about the full song structure
2. Scan this section for clichés
3. Analyze the syllable pattern

Provide feedback on:
1. How well this section works within the song
2. Lyrical quality and originality
3. Rhythm and flow
4. Specific line-by-line suggestions if needed"""
