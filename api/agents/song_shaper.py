"""
Song Shaper agent for new song exploration.

This agent guides users through discovering their song's shape while
ACTUALLY CREATING song data (sections, notes, metadata) in real-time.
The user sees their song take shape as they converse.

Key principles:
- Guide, don't generate lyrics
- Ask questions to surface the user's vision
- CREATE REAL SONG DATA when user validates ideas
- User sees sections appear, notes update in real-time
"""

import json
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from api.enums import NoteType, SectionType
from api.models import Song, SongNote, SongSection
from api.services.db_store import SongDBStore
from api.services.song_note_store import SongNoteStore


logger = logging.getLogger(__name__)

MAX_CONVERSATION_TURNS = 15

# Type alias for session factory (for concurrent operations)
SessionFactory = Callable[[], AsyncSession]


@dataclass
class SongShaperDependencies:
    """Dependencies for the Song Shaper agent."""

    song: Song
    session_factory: SessionFactory  # For creating sessions in tools
    conversation_history: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]


SONG_SHAPER_SYSTEM_PROMPT = """You are a Song Exploration Guide - you help songwriters discover and BUILD their song in real-time.

## Your Role
You're a creative collaborator who:
- Asks probing questions to surface themes, emotions, and imagery
- Identifies patterns in what the user shares
- CREATES actual song structure when user validates ideas
- Guides the user toward clarity WITHOUT writing lyrics for them

## CRITICAL: YOU CREATE REAL SONG DATA

Unlike a simple chatbot, you have tools that CREATE ACTUAL SONG DATA:
- `create_sections` - Creates real sections (Verse, Chorus, Bridge, etc.) in the song
- `set_theme` - Sets the song's theme (visible in metadata panel)
- `add_key_image` - Adds key images/phrases as notes
- `set_emotional_arc` - Sets the emotional journey
- `update_song_title` - Updates the song title

When you call these tools, the user IMMEDIATELY sees changes in their song editor.

## NEVER Write Lyrics
You are NOT a lyricist. You:
- ❌ Never write verses, choruses, or lines
- ❌ Never suggest specific word choices for lyrics
- ❌ Never complete or extend the user's fragments
- ✅ Acknowledge fragments the user shares
- ✅ Identify patterns and themes
- ✅ CREATE STRUCTURE when they validate ideas

## Conversation Flow

### Phase 1: Intake (1-2 exchanges)
Understand what the user has:
- A theme? Ask what it means to them personally
- Fragments/lines? Ask what feelings they evoke
- A feeling? Ask for a moment or image that captures it
- A reference song? Ask what aspect they connect with

### Phase 2: Exploration (3-6 exchanges)
Go deeper:
- "What's the turning point in this story?"
- "When does hope enter?" / "When does the pain peak?"
- "What do you want the listener to feel at the END?"
- "Are there images that keep coming back to you?"

AS YOU DISCOVER THINGS, use tools to capture them:
- Identify a theme? → Call `set_theme`
- User shares a powerful image? → Call `add_key_image`
- Understand the emotional journey? → Call `set_emotional_arc`

### Phase 3: Structure Creation (1-2 exchanges)
When you have enough context, propose AND CREATE structure:
- "Based on what you've shared, I see a structure like: Verse, Chorus, Verse, Chorus, Bridge, Chorus"
- "Want me to create this structure for you?"
- When they confirm → Call `create_sections` to ACTUALLY CREATE the sections
- The sections will appear in their editor immediately!

### Phase 4: Ready to Write
After creating sections:
- "Your song structure is ready! You can see the sections in the editor now."
- "Each section has notes about its intent. You can start writing lyrics!"
- They can now click into any section and start writing

## Tool Usage Guidelines

### set_theme
Call when you understand the core concept:
```
set_theme(theme="Finding hope after loss", notes="Personal journey of healing")
```

### add_key_image
Call when user shares a powerful image or phrase:
```
add_key_image(text="morning light through the window", category="visual")
```
Categories: "visual", "emotional", "temporal", "metaphor", "general"

### set_emotional_arc
Call when you understand the emotional journey:
```
set_emotional_arc(start="grief", end="acceptance", turning_point="the memory that brings peace")
```

### create_sections
Call when user validates a structure. This creates REAL sections:
```
create_sections(sections_json='[
  {"type": "verse", "number": 1, "intent": "Set the scene - the empty house"},
  {"type": "chorus", "intent": "The hook - finding light"},
  {"type": "verse", "number": 2, "intent": "The memory that changes everything"},
  {"type": "chorus", "intent": "Hook with new meaning"},
  {"type": "bridge", "intent": "The turning point"},
  {"type": "chorus", "intent": "Final emotional release"}
]')
```

### add_reference
Call when user mentions songs/artists they want to sound like:
```
add_reference(name="Dancing in the Moonlight", aspect="carefree vibe, catchy chorus")
```

## Example Interaction

User: "I want to write about an elusive speakeasy called The Green Flamingo"

You: Ask about theme, vibe, emotions...

[After exploration...]

User: "I like the structure you suggested. Let's do: Verse, Chorus, Verse, Chorus, Bridge, Verse, Chorus"

You:
1. Call `set_theme(theme="A mysterious speakeasy where everyone belongs")`
2. Call `set_emotional_arc(start="curiosity", end="joy and belonging", turning_point="discovering the bar's secret")`
3. Call `create_sections` with all 7 sections and their intents
4. Say: "Done! I've created 7 sections in your song. You can see them in the editor now. Each one has notes about what it should convey. Ready to start writing?"

## Important Notes
- The song editor is the "canvas" - always visible to the user
- When you create sections, they APPEAR in the editor immediately
- Notes you add are visible in the metadata panel
- You're helping them BUILD, not just plan"""


# Create the song shaper agent
song_shaper_agent = Agent(
    "openai:gpt-4o-mini",
    deps_type=SongShaperDependencies,
    system_prompt=SONG_SHAPER_SYSTEM_PROMPT,
)


# =============================================================================
# Agent tools - These create REAL song data
# =============================================================================


@song_shaper_agent.tool
async def get_current_song_state(ctx: RunContext[SongShaperDependencies]) -> str:
    """Get the current state of the song - what sections and notes exist."""
    song = ctx.deps.song

    parts = [f"Song: {song.title}"]

    # List sections
    if song.sections:
        parts.append(f"\nSections ({len(song.sections)}):")
        for section in sorted(song.sections, key=lambda s: s.order):
            section_name = f"{section.type.value.upper()}"
            if section.number:
                section_name += f" {section.number}"
            notes_preview = f" - {section.notes[:50]}..." if section.notes and len(section.notes) > 50 else f" - {section.notes}" if section.notes else ""
            parts.append(f"  {section.order + 1}. {section_name}{notes_preview}")
    else:
        parts.append("\nNo sections yet - this is a blank canvas.")

    # List relevant notes
    if song.song_notes:
        theme_notes = [n for n in song.song_notes if n.note_type == NoteType.THEME]
        arc_notes = [n for n in song.song_notes if n.note_type == NoteType.EMOTIONAL_ARC]
        image_notes = [n for n in song.song_notes if n.note_type == NoteType.KEY_IMAGE]

        if theme_notes:
            parts.append(f"\nTheme: {theme_notes[0].content}")
        if arc_notes:
            parts.append(f"\nEmotional Arc: {arc_notes[0].content}")
        if image_notes:
            parts.append(f"\nKey Images ({len(image_notes)}):")
            for note in image_notes[:5]:
                parts.append(f"  - {note.content}")

    return "\n".join(parts)


@song_shaper_agent.tool
async def set_theme(
    ctx: RunContext[SongShaperDependencies],
    theme: str,
    notes: Optional[str] = None,
) -> str:
    """Set or update the song's theme. This is visible in the metadata panel.

    Args:
        theme: The core theme or central idea (e.g., "hope after heartbreak")
        notes: Optional additional context about the theme
    """
    async with ctx.deps.session_factory() as session:
        note_store = SongNoteStore(session)

        # Check if theme note already exists
        existing = await note_store.list_by_song(ctx.deps.song.id, note_type=NoteType.THEME)

        content = theme
        if notes:
            content = f"{theme}\n\n{notes}"

        if existing:
            # Update existing theme
            await note_store.update(existing[0].id, {"content": content})
        else:
            # Create new theme note
            note = SongNote(
                song_id=ctx.deps.song.id,
                note_type=NoteType.THEME,
                title="Theme",
                content=content,
            )
            await note_store.create(note)

    logger.info(f"Set theme for song {ctx.deps.song.id}: {theme}")
    return f"✓ Theme set: {theme}"


@song_shaper_agent.tool
async def add_key_image(
    ctx: RunContext[SongShaperDependencies],
    text: str,
    category: str = "general",
) -> str:
    """Add a key image or phrase to the song. Visible in metadata panel.

    Args:
        text: The image or phrase (e.g., "morning light", "mom waving from porch")
        category: Type - "visual", "emotional", "temporal", "metaphor", or "general"
    """
    async with ctx.deps.session_factory() as session:
        note_store = SongNoteStore(session)

        note = SongNote(
            song_id=ctx.deps.song.id,
            note_type=NoteType.KEY_IMAGE,
            title=f"Key Image ({category})",
            content=text,
        )
        await note_store.create(note)

    logger.info(f"Added key image for song {ctx.deps.song.id}: {text}")
    return f"✓ Added key image: '{text}' ({category})"


@song_shaper_agent.tool
async def set_emotional_arc(
    ctx: RunContext[SongShaperDependencies],
    start: str,
    end: str,
    turning_point: Optional[str] = None,
) -> str:
    """Set the emotional arc of the song. Visible in metadata panel.

    Args:
        start: Where the song begins emotionally (e.g., "longing", "confusion")
        end: Where the song ends emotionally (e.g., "hope", "acceptance")
        turning_point: Optional - the moment where things shift
    """
    async with ctx.deps.session_factory() as session:
        note_store = SongNoteStore(session)

        # Build arc description
        arc_parts = [f"Start: {start}", f"End: {end}"]
        if turning_point:
            arc_parts.insert(1, f"Turning Point: {turning_point}")
        content = "\n".join(arc_parts)

        # Check if arc note already exists
        existing = await note_store.list_by_song(ctx.deps.song.id, note_type=NoteType.EMOTIONAL_ARC)

        if existing:
            await note_store.update(existing[0].id, {"content": content})
        else:
            note = SongNote(
                song_id=ctx.deps.song.id,
                note_type=NoteType.EMOTIONAL_ARC,
                title="Emotional Arc",
                content=content,
            )
            await note_store.create(note)

    arc_str = f"{start} → {turning_point} → {end}" if turning_point else f"{start} → {end}"
    logger.info(f"Set emotional arc for song {ctx.deps.song.id}: {arc_str}")
    return f"✓ Emotional arc set: {arc_str}"


@song_shaper_agent.tool
async def add_reference(
    ctx: RunContext[SongShaperDependencies],
    name: str,
    aspect: str = "",
) -> str:
    """Add a reference song/artist. Visible in metadata panel.

    Args:
        name: The song or artist name
        aspect: What aspect they connect with (e.g., "melodic vibe", "lyrical style")
    """
    async with ctx.deps.session_factory() as session:
        note_store = SongNoteStore(session)

        content = name
        if aspect:
            content = f"{name} - {aspect}"

        note = SongNote(
            song_id=ctx.deps.song.id,
            note_type=NoteType.REFERENCE,
            title="Reference",
            content=content,
        )
        await note_store.create(note)

    logger.info(f"Added reference for song {ctx.deps.song.id}: {name}")
    return f"✓ Added reference: {name}" + (f" ({aspect})" if aspect else "")


@song_shaper_agent.tool
async def add_fragment(
    ctx: RunContext[SongShaperDependencies],
    fragment: str,
) -> str:
    """Capture a lyric fragment the user shared (without modifying it).

    Args:
        fragment: The exact words the user shared
    """
    async with ctx.deps.session_factory() as session:
        note_store = SongNoteStore(session)

        note = SongNote(
            song_id=ctx.deps.song.id,
            note_type=NoteType.FRAGMENT,
            title="Fragment",
            content=fragment,
        )
        await note_store.create(note)

    logger.info(f"Added fragment for song {ctx.deps.song.id}: {fragment[:50]}...")
    return f'✓ Captured fragment: "{fragment}"'


@song_shaper_agent.tool
async def create_sections(
    ctx: RunContext[SongShaperDependencies],
    sections_json: str,
) -> str:
    """Create actual song sections. These appear in the editor immediately!

    Args:
        sections_json: JSON array of sections to create. Each section needs:
            - type: section type (verse, chorus, bridge, intro, outro, pre-chorus, post-chorus, instrumental, solo, breakdown)
            - intent: what this section does (e.g., "Sets the scene", "The emotional hook")
            - number: optional section number for verses/choruses (e.g., 1, 2)

    Example: '[{"type": "verse", "number": 1, "intent": "Set the scene"}, {"type": "chorus", "intent": "The hook"}]'
    """
    try:
        sections_data = json.loads(sections_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {e}"

    if not isinstance(sections_data, list):
        return "Error: sections_json must be a JSON array"

    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        created_sections = []
        for i, section_data in enumerate(sections_data):
            section_type_str = section_data.get("type", "verse").lower().replace("_", "-")

            # Map to SectionType enum
            try:
                section_type = SectionType(section_type_str)
            except ValueError:
                section_type = SectionType.OTHER

            intent = section_data.get("intent", "")
            number = section_data.get("number")

            section = SongSection(
                song_id=ctx.deps.song.id,
                type=section_type,
                number=number,
                order=i,
                notes=intent,
            )

            await db_store.add_section(ctx.deps.song.id, section)

            section_name = section_type.value.upper()
            if number:
                section_name += f" {number}"
            created_sections.append(f"{section_name}: {intent}")

    logger.info(f"Created {len(created_sections)} sections for song {ctx.deps.song.id}")

    result_lines = [f"✓ Created {len(created_sections)} sections:"]
    for i, section in enumerate(created_sections):
        result_lines.append(f"  {i + 1}. {section}")
    result_lines.append("\nThe sections are now visible in the song editor!")

    return "\n".join(result_lines)


@song_shaper_agent.tool
async def update_song_title(
    ctx: RunContext[SongShaperDependencies],
    title: str,
) -> str:
    """Update the song's title.

    Args:
        title: The new title for the song
    """
    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)
        await db_store.update(ctx.deps.song.id, {"title": title})

    logger.info(f"Updated title for song {ctx.deps.song.id}: {title}")
    return f"✓ Song title updated to: {title}"


# =============================================================================
# Helper functions
# =============================================================================


def build_shaper_prompt(
    user_message: str,
    conversation_history: list[dict],
    song: Song,
) -> str:
    """
    Build the prompt for the song shaper including conversation history.

    Args:
        user_message: The current user message
        conversation_history: Previous conversation turns
        song: The current song

    Returns:
        The formatted prompt string
    """
    parts = []

    # Add current song context
    song_context = [f"Current song: {song.title}"]
    if song.sections:
        song_context.append(f"Sections: {len(song.sections)}")
    else:
        song_context.append("Sections: None yet (blank canvas)")
    parts.append("\n".join(song_context))

    # Add conversation history
    if conversation_history:
        context_parts = []
        for turn in conversation_history[-MAX_CONVERSATION_TURNS:]:
            role = "User" if turn["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {turn['content']}")

        if context_parts:
            parts.append(f"Previous conversation:\n" + "\n".join(context_parts))

    # Add current message
    parts.append(f"Current message from user: {user_message}")

    # Add guidance based on conversation state
    if not conversation_history:
        parts.append(
            "\nThis is the START of the exploration. "
            "Acknowledge what they've shared and ask 2-3 questions to understand their vision. "
            "Use tools to capture any clear themes or images they mention."
        )
    elif song.sections:
        parts.append(
            "\nThe song already has sections. Help them refine or add more structure. "
            "You can create additional sections or update notes as needed."
        )

    return "\n\n".join(parts)
