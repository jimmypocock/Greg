"""
Orchestrator agent for conversational songwriting assistance.

This agent enables interactive conversations about songs, helping with
lyrics, structure, themes, and creative direction while staying focused
on songwriting topics.
"""

from dataclasses import dataclass
from pydantic_ai import Agent, RunContext

from apps.songwriter.models import Song
from apps.songwriter.agents.tools import (
    detect_cliches,
    count_syllables,
    get_song_lyrics,
    get_song_sections,
    get_song_metadata,
    get_song_summary,
)


# Maximum conversation history to include (to manage context window)
MAX_CONVERSATION_TURNS = 10


@dataclass
class OrchestratorDependencies:
    """Dependencies for the Orchestrator agent."""
    song: Song
    conversation_history: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]


# System prompt focused on songwriting assistance with guardrails
ORCHESTRATOR_SYSTEM_PROMPT = """You are a Songwriting Assistant - a knowledgeable collaborator who helps songwriters develop and improve their songs.

## CRITICAL: Always Fetch Song Content First
Before responding to ANY request about the song, you MUST use the get_lyrics tool to fetch the current lyrics. Do not ask the user to provide lyrics - you have access to them through the tools. This is essential for providing relevant, grounded feedback.

## Your Role
You help with:
- Analyzing and improving lyrics
- Suggesting rhymes and word choices
- Discussing themes and emotional direction
- Structural advice (verse, chorus, bridge arrangements)
- Creative brainstorming for song ideas
- Identifying and fixing cliches
- Rhythm and meter analysis

## Guidelines
1. ALWAYS call get_lyrics first before giving any feedback about the song content.

2. Stay focused on songwriting. If asked about unrelated topics, politely redirect: "I'm here to help with your song. What aspect would you like to work on?"

3. Be collaborative, not prescriptive. Offer options and explain your reasoning.

4. Be concise but helpful. Long responses should be reserved for detailed analysis when requested.

5. When suggesting lyric changes, provide multiple options when possible.

## Available Tools
- get_lyrics: Get the full lyrics (USE THIS FIRST)
- get_sections: See the song structure
- get_metadata: Get song info (key, tempo, title)
- get_summary: Quick overview of the song
- scan_for_cliches: Find overused phrases in given text
- analyze_syllables: Count syllables in given text

## Boundaries
- Only discuss topics related to songwriting and music
- Don't write entire songs from scratch - help improve what exists
- Don't engage with requests unrelated to the current song
- If the song has no content yet, help brainstorm ideas for it"""


# Create the orchestrator agent
orchestrator_agent = Agent(
    "openai:gpt-4o-mini",
    deps_type=OrchestratorDependencies,
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
)


# Register tools with the agent
@orchestrator_agent.tool
def get_lyrics(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Get the full lyrics of the current song."""
    return get_song_lyrics(ctx.deps.song)


@orchestrator_agent.tool
def get_sections(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Get information about the song's sections."""
    return get_song_sections(ctx.deps.song)


@orchestrator_agent.tool
def get_metadata(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Get metadata about the current song."""
    return get_song_metadata(ctx.deps.song)


@orchestrator_agent.tool
def get_summary(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Get a summary of the current song."""
    return get_song_summary(ctx.deps.song)


@orchestrator_agent.tool_plain
def scan_for_cliches(text: str) -> str:
    """Scan lyrics for common songwriting cliches and overused phrases."""
    return detect_cliches(text)


@orchestrator_agent.tool_plain
def analyze_syllables(text: str) -> str:
    """Count syllables in lyrics to check meter and rhythm."""
    return count_syllables(text)


def build_chat_prompt(user_message: str, conversation_history: list[dict]) -> str:
    """
    Build the prompt for the orchestrator including conversation history.

    Args:
        user_message: The current user message
        conversation_history: Previous conversation turns (already limited)

    Returns:
        The formatted prompt string
    """
    # Build context from recent conversation
    if conversation_history:
        context_parts = []
        for turn in conversation_history[-MAX_CONVERSATION_TURNS:]:
            role = "User" if turn["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {turn['content']}")

        conversation_context = "\n".join(context_parts)

        return f"""Previous conversation:
{conversation_context}

Current message from user: {user_message}

Remember: Use get_lyrics to fetch the song content if you haven't already, then respond helpfully."""

    return f"""User message: {user_message}

IMPORTANT: This is the start of a new conversation. First, use the get_lyrics tool to fetch the song's lyrics, then respond to the user's request with specific, grounded feedback based on the actual content."""
