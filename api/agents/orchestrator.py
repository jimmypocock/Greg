"""
Unified Orchestrator agent for songwriting collaboration.

This agent is the single conversational interface for all songwriting tasks:
- Exploring ideas and building song shape
- Creating and restructuring sections
- Writing and refining lyrics
- Giving feedback and analysis

The agent adapts its approach based on context (song state + conversation).
"""

import json
import logging
from dataclasses import dataclass
from typing import Callable, Optional

from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from api.enums import NoteType, SectionType
from api.database.models import Song, SongNote, SongSection
from api.services.db_store import SongDBStore
from api.services.song_note_store import SongNoteStore
from api.agents.tools import (
    detect_cliches,
    count_syllables,
    get_song_lyrics,
    get_song_sections,
    get_song_metadata,
)

logger = logging.getLogger(__name__)

# Maximum conversation history to include
MAX_CONVERSATION_TURNS = 15

# Type alias for session factory (for concurrent DB operations)
SessionFactory = Callable[[], AsyncSession]


@dataclass
class OrchestratorDependencies:
    """Dependencies for the Orchestrator agent."""

    song: Song
    session_factory: SessionFactory
    conversation_history: list[dict]  # [{"role": "user"|"assistant", "content": "..."}]
    system_prompt: str = ""  # Dynamic system prompt, set per-request


# =============================================================================
# System Prompt - Base + Context-Aware Guidance
# =============================================================================

BASE_SYSTEM_PROMPT = """You are a songwriting collaborator - a creative partner who helps bring songs to life.

## MANDATORY: YOU MUST USE TOOLS

You have tools that directly modify the song. When the user asks you to change something,
YOU MUST CALL THE APPROPRIATE TOOL. Never just describe what the change would look like.

**WRONG - Never do this:**
```
"The song has been restructured! Here's the new layout:
[SLOT 1] VERSE..."
```
This is WRONG because you didn't call any tool - you just wrote text.

**RIGHT - Always do this:**
1. Call get_song_state to see current structure
2. Call replace_structure (or other tool) to make the change
3. Then briefly confirm: "Done! I've restructured the song."

**Action words that REQUIRE tool calls:**
- "structure", "restructure", "organize" → call replace_structure or create_sections
- "write lyrics", "add lyrics" → call write_to_slot
- "delete", "remove" → call delete_section or delete_sections
- "move", "reorder" → call move_section or reorder_sections

If you respond with a formatted structure but didn't call replace_structure, YOU FAILED.
The user cannot see your text as changes - only tool calls modify the actual song.

## Response Format After Actions

After using tools, keep your response SHORT:
- "Done! I've restructured the song with 9 sections." (Good)
- "Here's the full layout: [SLOT 1]..." (Bad - too verbose, repeats what tools did)

The user will see the changes in the editor - you don't need to list everything.

## Your Capabilities
You can do ANYTHING to help with songwriting:
- Explore ideas and ask questions to understand the vision
- Create song structure (verses, choruses, bridges, etc.)
- Write lyrics, draft lines, suggest alternatives
- Give feedback on existing content
- Restructure and reorganize sections
- Capture themes, imagery, and emotional arcs

## How You Work
You have tools that CREATE and MODIFY the song in real-time:
- When you create sections, they appear in the editor immediately
- When you write lyrics, they're added to the song
- When you set themes or imagery, they're saved as notes
- The user sees all changes as they happen

## Understanding Song Structure
Every section in the song has a SLOT NUMBER (1, 2, 3, etc.) shown in get_song_state.
Use these slot numbers to reference sections - they're like line numbers in code.

Example structure:
```
[SLOT 1] VERSE 1 - Sets the scene
[SLOT 2] CHORUS - The hook
[SLOT 3] VERSE 2 - Development
```

When restructuring, you have FULL CONTROL:
- `delete_section(slot=2)` - Remove the chorus
- `move_section(from_slot=3, to_slot=1)` - Move verse 2 to the beginning
- `replace_structure(...)` - Clear everything and start fresh

ALWAYS check current structure with get_song_state before modifying!

## Your Approach
- Be a collaborator, not just an assistant
- TAKE ACTION - use tools to make changes, don't just describe them
- If they want to explore, ask great questions
- If they want content, WRITE IT with tools
- If they want structure changes, MAKE THEM with tools
- Always stay focused on the song at hand
- CHECK structure before making changes
- Use replace_structure when reorganizing (don't just append)

## Available Tools

**Reading (always start here):**
- `get_song_state` - Full overview with SLOT NUMBERS - call this first!
- `get_lyrics` - Get all lyrics
- `get_sections` - Get section structure
- `get_metadata` - Get song info (title, key, tempo)

**Structure Control (use slot numbers):**
- `create_sections` - ADD sections (appends to existing)
- `replace_structure` - REPLACE all sections (clears first) - use for reorganizing!
- `delete_section` - Remove one section by slot number
- `delete_sections` - Remove multiple sections ("1,3,5" or "all")
- `move_section` - Move section from one slot to another
- `reorder_sections` - Completely reorder all sections ("3,1,4,2")
- `update_song_title` - Change the title

**Writing Content (prefer slot-based):**
- `write_to_slot` - Add lyrics by slot number (preferred)
- `replace_slot_lyrics` - Replace lyrics by slot number (preferred)
- `write_lyrics` - Add lyrics by section type (fallback)
- `update_lyrics` - Replace lyrics by section type (fallback)

**Capturing Ideas:**
- `set_theme` - Set the song's theme
- `add_key_image` - Capture key imagery/phrases
- `set_emotional_arc` - Define the emotional journey
- `add_reference` - Note reference songs/artists
- `add_fragment` - Save lyric fragments

**Analysis:**
- `scan_for_cliches` - Find overused phrases
- `analyze_syllables` - Check meter and rhythm
"""

EXPLORATION_GUIDANCE = """
## Current Phase: Exploration
The song is in early stages. Focus on understanding the vision:
- Ask probing questions: "What's the turning point?" "What should listeners feel at the end?"
- Surface themes, emotions, key images from what they share
- Capture insights with tools (set_theme, add_key_image, set_emotional_arc)
- When you have enough context, propose a structure
- When they're ready, create sections AND draft initial content
"""

WRITING_GUIDANCE = """
## Current Phase: Writing
The song has structure but needs content. Focus on filling it out:
- Help draft lyrics for each section
- Reference the section notes/intent to guide tone
- Consider the emotional arc - where is this section in the journey?
- Offer options and alternatives when helpful
- Use write_lyrics to add content to sections
"""

REFINEMENT_GUIDANCE = """
## Current Phase: Refinement
The song has content to work with. Focus on making it better:
- Give specific, actionable feedback on existing lyrics
- Check for clichés, rhythm issues, unclear imagery
- Suggest alternatives for weak lines
- Help with rhyme schemes and meter
- Use update_lyrics when making changes to sections
"""


def build_system_prompt(song: Song, conversation_history: list[dict]) -> str:
    """
    Build the system prompt with context-aware guidance.

    Analyzes the song state and conversation to determine which
    phase guidance to include.
    """
    # Analyze song state
    has_real_sections = bool(song.sections) and any(
        s.type != SectionType.BRAIN_DUMP for s in song.sections
    )

    has_lyrics = False
    if has_real_sections:
        for section in song.sections:
            if section.type == SectionType.BRAIN_DUMP:
                continue
            # Check if section has lines with content
            main_version = section.main_version
            if main_version and main_version.lines:
                if any(line.text.strip() for line in main_version.lines):
                    has_lyrics = True
                    break

    is_early_conversation = len(conversation_history) < 6

    # Build prompt with appropriate guidance
    guidance_blocks = []

    # Exploration phase: no real sections OR early in conversation
    if not has_real_sections or (not has_lyrics and is_early_conversation):
        guidance_blocks.append(EXPLORATION_GUIDANCE)

    # Writing phase: has sections but no/little lyrics
    if has_real_sections and not has_lyrics:
        guidance_blocks.append(WRITING_GUIDANCE)

    # Refinement phase: has lyrics
    if has_lyrics:
        guidance_blocks.append(REFINEMENT_GUIDANCE)

    # If no specific phase detected, include all (flexible mode)
    if not guidance_blocks:
        guidance_blocks = [EXPLORATION_GUIDANCE, WRITING_GUIDANCE, REFINEMENT_GUIDANCE]

    return BASE_SYSTEM_PROMPT + "\n\n" + "\n\n".join(guidance_blocks)


# =============================================================================
# Create the Agent
# =============================================================================

# Note: System prompt is set dynamically via build_system_prompt()
# We use a minimal default here; the actual prompt is passed per-request
orchestrator_agent = Agent(
    "openai:gpt-5.2",  # GPT-5.2 has 98.7% tool use accuracy - best for structure control
    deps_type=OrchestratorDependencies,
)


@orchestrator_agent.system_prompt
def dynamic_system_prompt(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Return the dynamic system prompt from dependencies, or default."""
    if ctx.deps.system_prompt:
        return ctx.deps.system_prompt
    return BASE_SYSTEM_PROMPT


# =============================================================================
# Tools: Reading
# =============================================================================


@orchestrator_agent.tool
async def get_song_state(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Get the full current state of the song - sections, lyrics, notes, everything.

    Returns a structured view with SLOT NUMBERS for each section.
    Use slot numbers to reference sections in delete_section, move_section, etc.
    """
    song = ctx.deps.song

    parts = [f"# {song.title}"]

    # Metadata
    meta_parts = []
    if song.key:
        meta_parts.append(f"Key: {song.key}")
    if song.tempo:
        meta_parts.append(f"Tempo: {song.tempo} BPM")
    if song.time_signature:
        meta_parts.append(f"Time: {song.time_signature}")
    if meta_parts:
        parts.append(" | ".join(meta_parts))

    # Theme and arc from notes
    if song.song_notes:
        theme_notes = [n for n in song.song_notes if n.note_type == NoteType.THEME]
        arc_notes = [n for n in song.song_notes if n.note_type == NoteType.EMOTIONAL_ARC]
        image_notes = [n for n in song.song_notes if n.note_type == NoteType.KEY_IMAGE]

        if theme_notes:
            parts.append(f"\n**Theme:** {theme_notes[0].content}")
        if arc_notes:
            parts.append(f"**Emotional Arc:** {arc_notes[0].content}")
        if image_notes:
            parts.append(f"**Key Images:** {', '.join(n.content for n in image_notes[:5])}")

    # Sections with lyrics - now with SLOT NUMBERS for reference
    if song.sections:
        real_sections = [s for s in song.sections if s.type != SectionType.BRAIN_DUMP]
        if real_sections:
            parts.append(f"\n## Structure ({len(real_sections)} sections)")
            parts.append("Use SLOT numbers below to reference sections in tools.\n")

            sorted_sections = sorted(real_sections, key=lambda s: s.order)
            for slot, section in enumerate(sorted_sections, 1):
                section_name = section.type.value.upper()
                if section.number:
                    section_name += f" {section.number}"

                # Show slot number prominently
                section_header = f"### [SLOT {slot}] {section_name}"
                if section.notes:
                    section_header += f"\n*Intent: {section.notes}*"
                parts.append(section_header)

                # Get lyrics from main version
                main_version = section.main_version
                if main_version and main_version.lines:
                    lines = sorted(main_version.lines, key=lambda l: l.order)
                    lyrics = [line.text for line in lines if line.text.strip()]
                    if lyrics:
                        parts.append("\n".join(lyrics))
                    else:
                        parts.append("*(empty - no lyrics yet)*")
                else:
                    parts.append("*(empty - no lyrics yet)*")

            # Show structure summary for quick reference
            structure_str = " → ".join(
                f"[{i+1}]{s.type.value}" + (f"{s.number}" if s.number else "")
                for i, s in enumerate(sorted_sections)
            )
            parts.append(f"\n**Current flow:** {structure_str}")
        else:
            parts.append("\n*No sections yet - blank canvas*")
    else:
        parts.append("\n*No sections yet - blank canvas*")

    return "\n".join(parts)


@orchestrator_agent.tool
def get_lyrics(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Get just the lyrics of the current song."""
    return get_song_lyrics(ctx.deps.song)


@orchestrator_agent.tool
def get_sections(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Get information about the song's section structure."""
    return get_song_sections(ctx.deps.song)


@orchestrator_agent.tool
def get_metadata(ctx: RunContext[OrchestratorDependencies]) -> str:
    """Get metadata about the current song (title, key, tempo, etc.)."""
    return get_song_metadata(ctx.deps.song)


# =============================================================================
# Tools: Creating Structure
# =============================================================================


@orchestrator_agent.tool
async def create_sections(
    ctx: RunContext[OrchestratorDependencies],
    sections_json: str,
) -> str:
    """Create song sections. These appear in the editor immediately!

    Args:
        sections_json: JSON array of sections. Each section needs:
            - type: verse, chorus, bridge, intro, outro, pre-chorus, post-chorus, instrumental, solo, breakdown
            - intent: what this section conveys (e.g., "Sets the scene", "The emotional hook")
            - number: optional number for verses/choruses (1, 2, etc.)
            - lyrics: optional array of lyric lines to include

    Example: '[
        {"type": "verse", "number": 1, "intent": "Set the scene", "lyrics": ["First line", "Second line"]},
        {"type": "chorus", "intent": "The hook"}
    ]'
    """
    try:
        sections_data = json.loads(sections_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {e}"

    if not isinstance(sections_data, list):
        return "Error: sections_json must be a JSON array"

    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        # Get current max order
        existing_sections = ctx.deps.song.sections or []
        start_order = max((s.order for s in existing_sections), default=-1) + 1

        created_sections = []
        for i, section_data in enumerate(sections_data):
            section_type_str = section_data.get("type", "verse").lower().replace("_", "-")

            try:
                section_type = SectionType(section_type_str)
            except ValueError:
                section_type = SectionType.OTHER

            intent = section_data.get("intent", "")
            number = section_data.get("number")
            lyrics = section_data.get("lyrics", [])

            section = SongSection(
                song_id=ctx.deps.song.id,
                type=section_type,
                number=number,
                order=start_order + i,
                notes=intent,
            )

            created_section = await db_store.add_section(ctx.deps.song.id, section)

            # Add lyrics if provided
            if lyrics and isinstance(lyrics, list):
                from api.database.models import Line
                for j, lyric_text in enumerate(lyrics):
                    if isinstance(lyric_text, str) and lyric_text.strip():
                        line = Line(text=lyric_text.strip(), order=j)
                        await db_store.add_line(created_section.id, line)

            section_name = section_type.value.upper()
            if number:
                section_name += f" {number}"
            lyric_count = len([l for l in lyrics if l.strip()]) if lyrics else 0
            created_sections.append(f"{section_name}: {intent}" + (f" ({lyric_count} lines)" if lyric_count else ""))

    logger.info(f"Created {len(created_sections)} sections for song {ctx.deps.song.id}")

    result_lines = [f"✓ Created {len(created_sections)} sections:"]
    for i, section in enumerate(created_sections):
        result_lines.append(f"  {i + 1}. {section}")
    result_lines.append("\nThe sections are now visible in the song editor!")

    return "\n".join(result_lines)


@orchestrator_agent.tool
async def update_song_title(
    ctx: RunContext[OrchestratorDependencies],
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


@orchestrator_agent.tool
async def delete_section(
    ctx: RunContext[OrchestratorDependencies],
    slot: int,
) -> str:
    """Delete a section from the song by its slot number.

    Use get_song_state to see current slots. This PERMANENTLY removes the section
    and any lyrics it contains.

    Args:
        slot: The slot number (1, 2, 3, etc.) from get_song_state output
    """
    song = ctx.deps.song
    real_sections = [s for s in song.sections if s.type != SectionType.BRAIN_DUMP]
    sorted_sections = sorted(real_sections, key=lambda s: s.order)

    if slot < 1 or slot > len(sorted_sections):
        return f"Error: Invalid slot {slot}. Song has {len(sorted_sections)} sections (slots 1-{len(sorted_sections)})."

    target_section = sorted_sections[slot - 1]
    section_name = target_section.type.value.upper()
    if target_section.number:
        section_name += f" {target_section.number}"

    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)
        await db_store.delete_section(target_section.id)

    logger.info(f"Deleted section {section_name} (slot {slot}) from song {song.id}")
    return f"✓ Deleted [SLOT {slot}] {section_name}"


@orchestrator_agent.tool
async def delete_sections(
    ctx: RunContext[OrchestratorDependencies],
    slots: str,
) -> str:
    """Delete multiple sections by their slot numbers.

    Args:
        slots: Comma-separated slot numbers (e.g., "1,3,5") or "all" to clear everything
    """
    song = ctx.deps.song
    real_sections = [s for s in song.sections if s.type != SectionType.BRAIN_DUMP]
    sorted_sections = sorted(real_sections, key=lambda s: s.order)

    if not sorted_sections:
        return "No sections to delete - song is already empty."

    # Parse slots
    if slots.lower().strip() == "all":
        slots_to_delete = list(range(1, len(sorted_sections) + 1))
    else:
        try:
            slots_to_delete = [int(s.strip()) for s in slots.split(",")]
        except ValueError:
            return "Error: Invalid slots format. Use comma-separated numbers (e.g., '1,3,5') or 'all'."

    # Validate slots
    invalid_slots = [s for s in slots_to_delete if s < 1 or s > len(sorted_sections)]
    if invalid_slots:
        return f"Error: Invalid slots {invalid_slots}. Song has {len(sorted_sections)} sections (slots 1-{len(sorted_sections)})."

    # Delete in reverse order to maintain slot validity
    deleted = []
    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)
        for slot in sorted(slots_to_delete, reverse=True):
            section = sorted_sections[slot - 1]
            section_name = section.type.value.upper()
            if section.number:
                section_name += f" {section.number}"
            await db_store.delete_section(section.id)
            deleted.append(f"[{slot}] {section_name}")

    logger.info(f"Deleted {len(deleted)} sections from song {song.id}")
    return f"✓ Deleted {len(deleted)} sections:\n" + "\n".join(f"  - {d}" for d in reversed(deleted))


@orchestrator_agent.tool
async def move_section(
    ctx: RunContext[OrchestratorDependencies],
    from_slot: int,
    to_slot: int,
) -> str:
    """Move a section from one position to another.

    Args:
        from_slot: Current slot number of the section to move
        to_slot: Target slot number (where it should end up)

    Example: move_section(3, 1) moves section at slot 3 to become slot 1
    """
    song = ctx.deps.song
    real_sections = [s for s in song.sections if s.type != SectionType.BRAIN_DUMP]
    sorted_sections = sorted(real_sections, key=lambda s: s.order)
    n = len(sorted_sections)

    if from_slot < 1 or from_slot > n:
        return f"Error: from_slot {from_slot} invalid. Song has {n} sections (slots 1-{n})."
    if to_slot < 1 or to_slot > n:
        return f"Error: to_slot {to_slot} invalid. Song has {n} sections (slots 1-{n})."
    if from_slot == to_slot:
        return f"Section is already at slot {from_slot}. No change needed."

    # Get the section to move
    moving_section = sorted_sections[from_slot - 1]
    section_name = moving_section.type.value.upper()
    if moving_section.number:
        section_name += f" {moving_section.number}"

    # Calculate new order values
    # We need to reorder all affected sections
    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        # Build new order: remove from old position, insert at new
        sections_list = list(sorted_sections)
        sections_list.pop(from_slot - 1)
        sections_list.insert(to_slot - 1, moving_section)

        # Update order values for all sections
        for i, section in enumerate(sections_list):
            await db_store.update_section(section.id, {"order": i})

    logger.info(f"Moved {section_name} from slot {from_slot} to slot {to_slot} in song {song.id}")

    # Show new structure
    new_structure = " → ".join(
        f"[{i+1}]{s.type.value}" + (f"{s.number}" if s.number else "")
        for i, s in enumerate(sections_list)
    )
    return f"✓ Moved {section_name} from slot {from_slot} → slot {to_slot}\n\nNew structure: {new_structure}"


@orchestrator_agent.tool
async def reorder_sections(
    ctx: RunContext[OrchestratorDependencies],
    new_order: str,
) -> str:
    """Completely reorder all sections in one operation.

    Args:
        new_order: Comma-separated slot numbers in desired order.
                   Must include all current slots exactly once.
                   Example: "3,1,4,2" reorders 4 sections

    Example: If song has [1]VERSE → [2]CHORUS → [3]BRIDGE → [4]OUTRO
    calling reorder_sections("3,1,4,2") produces:
    [1]BRIDGE → [2]VERSE → [3]OUTRO → [4]CHORUS
    """
    song = ctx.deps.song
    real_sections = [s for s in song.sections if s.type != SectionType.BRAIN_DUMP]
    sorted_sections = sorted(real_sections, key=lambda s: s.order)
    n = len(sorted_sections)

    if n == 0:
        return "No sections to reorder."

    # Parse new order
    try:
        order_list = [int(s.strip()) for s in new_order.split(",")]
    except ValueError:
        return "Error: Invalid format. Use comma-separated numbers (e.g., '3,1,4,2')."

    # Validate
    if len(order_list) != n:
        return f"Error: Must specify all {n} slots. Got {len(order_list)} numbers."

    if set(order_list) != set(range(1, n + 1)):
        return f"Error: Must include each slot 1-{n} exactly once. Got: {order_list}"

    # Reorder
    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        # Map old slots to new positions
        for new_pos, old_slot in enumerate(order_list):
            section = sorted_sections[old_slot - 1]
            await db_store.update_section(section.id, {"order": new_pos})

    logger.info(f"Reordered sections in song {song.id}: {new_order}")

    # Build new structure string
    reordered = [sorted_sections[old_slot - 1] for old_slot in order_list]
    new_structure = " → ".join(
        f"[{i+1}]{s.type.value}" + (f"{s.number}" if s.number else "")
        for i, s in enumerate(reordered)
    )
    return f"✓ Sections reordered!\n\nNew structure: {new_structure}"


@orchestrator_agent.tool
async def replace_structure(
    ctx: RunContext[OrchestratorDependencies],
    sections_json: str,
    preserve_lyrics: bool = False,
) -> str:
    """Replace the entire song structure. DELETES all existing sections first!

    Use this when you want to restructure the song from scratch rather than
    adding to what's there. This is the cleanest way to reorganize.

    Args:
        sections_json: JSON array of new sections (same format as create_sections).
            Each section needs: type, intent, optional number, optional lyrics
        preserve_lyrics: If true, tries to match old section types to new ones and
            migrate lyrics. Default is false (clean slate).

    Example: '[ {"type": "verse", "number": 1, "intent": "Opening scene"},
               {"type": "chorus", "intent": "The hook"},
               {"type": "verse", "number": 2, "intent": "Development"} ]'
    """
    try:
        sections_data = json.loads(sections_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON - {e}"

    if not isinstance(sections_data, list):
        return "Error: sections_json must be a JSON array"

    song = ctx.deps.song
    real_sections = [s for s in song.sections if s.type != SectionType.BRAIN_DUMP]

    # Optionally preserve lyrics by type
    lyrics_by_type: dict[str, list[str]] = {}
    if preserve_lyrics and real_sections:
        for section in real_sections:
            main_version = section.main_version
            if main_version and main_version.lines:
                lines = sorted(main_version.lines, key=lambda l: l.order)
                lyrics = [line.text for line in lines if line.text.strip()]
                if lyrics:
                    type_key = f"{section.type.value}_{section.number or ''}"
                    lyrics_by_type[type_key] = lyrics

    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        # Delete all existing real sections
        deleted_count = 0
        for section in real_sections:
            await db_store.delete_section(section.id)
            deleted_count += 1

        # Create new sections
        created_sections = []
        for i, section_data in enumerate(sections_data):
            section_type_str = section_data.get("type", "verse").lower().replace("_", "-")

            try:
                section_type = SectionType(section_type_str)
            except ValueError:
                section_type = SectionType.OTHER

            intent = section_data.get("intent", "")
            number = section_data.get("number")
            lyrics = section_data.get("lyrics", [])

            # Check for preserved lyrics
            if preserve_lyrics and not lyrics:
                type_key = f"{section_type.value}_{number or ''}"
                if type_key in lyrics_by_type:
                    lyrics = lyrics_by_type.pop(type_key)  # Use once

            section = SongSection(
                song_id=song.id,
                type=section_type,
                number=number,
                order=i,
                notes=intent,
            )

            created_section = await db_store.add_section(song.id, section)

            # Add lyrics if provided
            if lyrics and isinstance(lyrics, list):
                from api.database.models import Line
                for j, lyric_text in enumerate(lyrics):
                    if isinstance(lyric_text, str) and lyric_text.strip():
                        line = Line(text=lyric_text.strip(), order=j)
                        await db_store.add_line(created_section.id, line)

            section_name = section_type.value.upper()
            if number:
                section_name += f" {number}"
            lyric_count = len([l for l in lyrics if isinstance(l, str) and l.strip()]) if lyrics else 0
            created_sections.append(f"[{i+1}] {section_name}: {intent}" + (f" ({lyric_count} lines)" if lyric_count else ""))

    logger.info(f"Replaced structure in song {song.id}: deleted {deleted_count}, created {len(created_sections)}")

    result_lines = [f"✓ Structure replaced! (removed {deleted_count} old sections)"]
    result_lines.append(f"\nNew structure ({len(created_sections)} sections):")
    for section in created_sections:
        result_lines.append(f"  {section}")

    return "\n".join(result_lines)


# =============================================================================
# Tools: Writing Content
# =============================================================================


@orchestrator_agent.tool
async def write_lyrics(
    ctx: RunContext[OrchestratorDependencies],
    section_type: str,
    lyrics: str,
    section_number: Optional[int] = None,
) -> str:
    """Write lyrics to a section. Adds lines to the section.

    Args:
        section_type: Type of section (verse, chorus, bridge, etc.)
        lyrics: The lyrics to add (one line per line, or separated by newlines)
        section_number: Optional section number (for "verse 1" vs "verse 2")
    """
    song = ctx.deps.song
    section_type_str = section_type.lower().replace("_", "-")

    # Find the matching section
    target_section = None
    for section in song.sections:
        if section.type.value == section_type_str:
            if section_number is None or section.number == section_number:
                target_section = section
                break

    if not target_section:
        section_desc = section_type.upper()
        if section_number:
            section_desc += f" {section_number}"
        return f"Error: Could not find section '{section_desc}'. Use get_sections to see available sections."

    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        # Get current max line order
        main_version = target_section.main_version
        existing_lines = main_version.lines if main_version else []
        start_order = max((l.order for l in existing_lines), default=-1) + 1

        # Parse and add lyrics
        from api.database.models import Line
        lines_added = 0
        for i, line_text in enumerate(lyrics.strip().split("\n")):
            if line_text.strip():
                line = Line(text=line_text.strip(), order=start_order + i)
                await db_store.add_line(target_section.id, line)
                lines_added += 1

    section_name = target_section.type.value.upper()
    if target_section.number:
        section_name += f" {target_section.number}"

    logger.info(f"Added {lines_added} lines to {section_name} in song {song.id}")
    return f"✓ Added {lines_added} lines to {section_name}"


@orchestrator_agent.tool
async def update_lyrics(
    ctx: RunContext[OrchestratorDependencies],
    section_type: str,
    lyrics: str,
    section_number: Optional[int] = None,
) -> str:
    """Replace all lyrics in a section with new content.

    Args:
        section_type: Type of section (verse, chorus, bridge, etc.)
        lyrics: The new lyrics (replaces existing content)
        section_number: Optional section number (for "verse 1" vs "verse 2")
    """
    song = ctx.deps.song
    section_type_str = section_type.lower().replace("_", "-")

    # Find the matching section
    target_section = None
    for section in song.sections:
        if section.type.value == section_type_str:
            if section_number is None or section.number == section_number:
                target_section = section
                break

    if not target_section:
        section_desc = section_type.upper()
        if section_number:
            section_desc += f" {section_number}"
        return f"Error: Could not find section '{section_desc}'. Use get_sections to see available sections."

    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        # Delete existing lines
        main_version = target_section.main_version
        if main_version and main_version.lines:
            for line in main_version.lines:
                await db_store.delete_line(target_section.id, line.id)

        # Add new lyrics
        from api.database.models import Line
        lines_added = 0
        for i, line_text in enumerate(lyrics.strip().split("\n")):
            if line_text.strip():
                line = Line(text=line_text.strip(), order=i)
                await db_store.add_line(target_section.id, line)
                lines_added += 1

    section_name = target_section.type.value.upper()
    if target_section.number:
        section_name += f" {target_section.number}"

    logger.info(f"Updated {section_name} with {lines_added} lines in song {song.id}")
    return f"✓ Updated {section_name} with {lines_added} lines"


@orchestrator_agent.tool
async def write_to_slot(
    ctx: RunContext[OrchestratorDependencies],
    slot: int,
    lyrics: str,
) -> str:
    """Write lyrics to a section by slot number. More reliable than write_lyrics.

    Args:
        slot: The slot number (1, 2, 3, etc.) from get_song_state
        lyrics: The lyrics to add (newline-separated)
    """
    song = ctx.deps.song
    real_sections = [s for s in song.sections if s.type != SectionType.BRAIN_DUMP]
    sorted_sections = sorted(real_sections, key=lambda s: s.order)

    if slot < 1 or slot > len(sorted_sections):
        return f"Error: Invalid slot {slot}. Song has {len(sorted_sections)} sections (slots 1-{len(sorted_sections)})."

    target_section = sorted_sections[slot - 1]
    section_name = target_section.type.value.upper()
    if target_section.number:
        section_name += f" {target_section.number}"

    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        main_version = target_section.main_version
        existing_lines = main_version.lines if main_version else []
        start_order = max((l.order for l in existing_lines), default=-1) + 1

        from api.database.models import Line
        lines_added = 0
        for i, line_text in enumerate(lyrics.strip().split("\n")):
            if line_text.strip():
                line = Line(text=line_text.strip(), order=start_order + i)
                await db_store.add_line(target_section.id, line)
                lines_added += 1

    logger.info(f"Added {lines_added} lines to slot {slot} ({section_name}) in song {song.id}")
    return f"✓ Added {lines_added} lines to [SLOT {slot}] {section_name}"


@orchestrator_agent.tool
async def replace_slot_lyrics(
    ctx: RunContext[OrchestratorDependencies],
    slot: int,
    lyrics: str,
) -> str:
    """Replace all lyrics in a section by slot number. More reliable than update_lyrics.

    Args:
        slot: The slot number (1, 2, 3, etc.) from get_song_state
        lyrics: The new lyrics (replaces existing content)
    """
    song = ctx.deps.song
    real_sections = [s for s in song.sections if s.type != SectionType.BRAIN_DUMP]
    sorted_sections = sorted(real_sections, key=lambda s: s.order)

    if slot < 1 or slot > len(sorted_sections):
        return f"Error: Invalid slot {slot}. Song has {len(sorted_sections)} sections (slots 1-{len(sorted_sections)})."

    target_section = sorted_sections[slot - 1]
    section_name = target_section.type.value.upper()
    if target_section.number:
        section_name += f" {target_section.number}"

    async with ctx.deps.session_factory() as session:
        db_store = SongDBStore(session)

        # Delete existing lines
        main_version = target_section.main_version
        if main_version and main_version.lines:
            for line in main_version.lines:
                await db_store.delete_line(target_section.id, line.id)

        # Add new lyrics
        from api.database.models import Line
        lines_added = 0
        for i, line_text in enumerate(lyrics.strip().split("\n")):
            if line_text.strip():
                line = Line(text=line_text.strip(), order=i)
                await db_store.add_line(target_section.id, line)
                lines_added += 1

    logger.info(f"Replaced lyrics in slot {slot} ({section_name}) with {lines_added} lines in song {song.id}")
    return f"✓ Replaced lyrics in [SLOT {slot}] {section_name} with {lines_added} lines"


# =============================================================================
# Tools: Capturing Ideas
# =============================================================================


@orchestrator_agent.tool
async def set_theme(
    ctx: RunContext[OrchestratorDependencies],
    theme: str,
    notes: Optional[str] = None,
) -> str:
    """Set or update the song's theme.

    Args:
        theme: The core theme or central idea (e.g., "hope after heartbreak")
        notes: Optional additional context about the theme
    """
    async with ctx.deps.session_factory() as session:
        note_store = SongNoteStore(session)

        existing = await note_store.list_by_song(ctx.deps.song.id, note_type=NoteType.THEME)

        content = theme
        if notes:
            content = f"{theme}\n\n{notes}"

        if existing:
            await note_store.update(existing[0].id, {"content": content})
        else:
            note = SongNote(
                song_id=ctx.deps.song.id,
                note_type=NoteType.THEME,
                title="Theme",
                content=content,
            )
            await note_store.create(note)

    logger.info(f"Set theme for song {ctx.deps.song.id}: {theme}")
    return f"✓ Theme set: {theme}"


@orchestrator_agent.tool
async def add_key_image(
    ctx: RunContext[OrchestratorDependencies],
    text: str,
    category: str = "general",
) -> str:
    """Add a key image or phrase to the song.

    Args:
        text: The image or phrase (e.g., "morning light", "empty chair at the table")
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


@orchestrator_agent.tool
async def set_emotional_arc(
    ctx: RunContext[OrchestratorDependencies],
    start: str,
    end: str,
    turning_point: Optional[str] = None,
) -> str:
    """Set the emotional arc of the song.

    Args:
        start: Where the song begins emotionally (e.g., "longing", "confusion")
        end: Where the song ends emotionally (e.g., "hope", "acceptance")
        turning_point: Optional - the moment where things shift
    """
    async with ctx.deps.session_factory() as session:
        note_store = SongNoteStore(session)

        arc_parts = [f"Start: {start}", f"End: {end}"]
        if turning_point:
            arc_parts.insert(1, f"Turning Point: {turning_point}")
        content = "\n".join(arc_parts)

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


@orchestrator_agent.tool
async def add_reference(
    ctx: RunContext[OrchestratorDependencies],
    name: str,
    aspect: str = "",
) -> str:
    """Add a reference song or artist.

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


@orchestrator_agent.tool
async def add_fragment(
    ctx: RunContext[OrchestratorDependencies],
    fragment: str,
) -> str:
    """Capture a lyric fragment or idea.

    Args:
        fragment: The text to save
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


# =============================================================================
# Tools: Analysis
# =============================================================================


@orchestrator_agent.tool_plain
def scan_for_cliches(text: str) -> str:
    """Scan text for common songwriting clichés and overused phrases.

    Args:
        text: The lyrics to analyze
    """
    return detect_cliches(text)


@orchestrator_agent.tool_plain
def analyze_syllables(text: str) -> str:
    """Count syllables in text to check meter and rhythm.

    Args:
        text: The lyrics to analyze
    """
    return count_syllables(text)


# =============================================================================
# Prompt Builder
# =============================================================================


def build_orchestrator_prompt(
    user_message: str,
    conversation_history: list[dict],
    song: Song,
) -> str:
    """
    Build the user prompt including conversation history and song context.

    Args:
        user_message: The current user message
        conversation_history: Previous conversation turns
        song: The current song

    Returns:
        The formatted prompt string
    """
    parts = []

    # Add song context summary
    song_context = [f"Current song: {song.title}"]

    real_sections = [s for s in (song.sections or []) if s.type != SectionType.BRAIN_DUMP]
    if real_sections:
        song_context.append(f"Sections: {len(real_sections)}")
        section_types = [s.type.value for s in sorted(real_sections, key=lambda x: x.order)]
        song_context.append(f"Structure: {' → '.join(section_types)}")
    else:
        song_context.append("Sections: None yet (blank canvas)")

    parts.append(" | ".join(song_context))

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

    return "\n\n".join(parts)
