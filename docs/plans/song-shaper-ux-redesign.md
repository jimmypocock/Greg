# Song Shaper UX Redesign

## Summary

Redesign the "new song" experience so users go directly to the song editor (the canvas) and chat with the AI there. The AI creates real song data (sections, notes, metadata) as they converse, rather than building an abstract "mindmap" that gets converted later.

## Current State (What We Have)

### Flow
1. `/songs/new` - Choice page (Explore with AI vs Paste Lyrics)
2. `/songs/new/chat` - Chat with AI, builds a "SongShape" mindmap
3. Click "Ready to Write" - Converts shape to sections
4. Redirect to `/songs/{id}` - The actual editor

### Problems
- The mindmap feels disconnected from the actual song
- User doesn't see the "canvas" until after the conversation
- When AI suggests structure, it's not creating real data
- Two separate experiences that should be one

## New Vision (What We Want)

### Flow
1. Create song → Go directly to `/songs/{id}` (the editor)
2. Chat with AI in the right panel (already exists)
3. AI creates REAL song data as you converse
4. User sees sections appear, metadata update in real-time

### The Canvas
The song editor already has the perfect layout:
- **Left panel**: Song metadata (title, tempo, key, etc.)
- **Middle panel**: Sections/lyrics editor (the canvas)
- **Right panel**: AI chat

This IS the canvas. No separate page needed.

### AI Behavior for New Songs
When a song is new/empty, the chat agent should:
1. Act as a "guided tour" - asking exploratory questions
2. Help discover theme, structure, key images, emotional arc
3. **Actually create song data** when user validates:
   - Create sections with intent notes
   - Update song metadata (theme in notes)
   - Store key images and emotional arc as song notes

### Example Interaction
```
User: "I want to write about an elusive speakeasy called The Green Flamingo"

AI: [Asks exploratory questions about theme, vibe, emotions...]

[After several exchanges...]

AI: "Based on what you've shared, here's the structure I see:
1. VERSE: Exploring the mysterious atmosphere
2. CHORUS: An anthem celebrating the Green Flamingo
3. VERSE: Personal encounters at the bar
..."

User: "This is perfect, let's make the song"

AI: [ACTUALLY CREATES]:
- 7 sections in the song (Verse, Chorus, Verse, Chorus, Bridge, Verse, Chorus)
- Each section has notes about its intent
- Song notes with theme, key images, emotional arc
- User SEES these appear in the editor
```

## Implementation Plan

### Phase 1: Update Shaper Agent Tools

**File: `api/agents/song_shaper.py`**

Replace shape-specific tools with song-data tools:

| Old Tool | New Tool | What It Does |
|----------|----------|--------------|
| `update_theme` | `update_song_notes` | Add theme to song notes |
| `add_key_image` | `add_song_note` | Store as note with type KEY_IMAGE |
| `update_emotional_arc` | `add_song_note` | Store as note with type EMOTIONAL_ARC |
| `suggest_structure` | `create_sections` | Actually create SongSection records |
| `add_fragment` | `add_song_note` | Store user's fragments as notes |

New tool signatures:
```python
@song_shaper_agent.tool
async def create_sections(
    ctx: RunContext[SongShaperDependencies],
    sections_json: str,  # [{"type": "verse", "intent": "...", "number": 1}, ...]
) -> str:
    """Create actual song sections with intent notes."""
    # Parse JSON, create SongSection records, return confirmation

@song_shaper_agent.tool
async def update_song_metadata(
    ctx: RunContext[SongShaperDependencies],
    title: Optional[str] = None,
    tempo: Optional[int] = None,
    key: Optional[str] = None,
    notes: Optional[str] = None,  # Theme goes here
) -> str:
    """Update the song's metadata."""
```

### Phase 2: Update Dependencies

**File: `api/agents/song_shaper.py`**

Change `SongShaperDependencies` to use `SongDBStore` instead of `SongShapeService`:

```python
@dataclass
class SongShaperDependencies:
    song: Song
    db_store: SongDBStore  # For creating sections, notes
    conversation_history: list[dict]
```

### Phase 3: Integrate Shaper into Song Editor

**Option A: Add shaper mode to existing orchestrator**
- When song has no sections, use shaper behavior
- When song has content, use normal orchestrator

**Option B: Use shaper agent for empty songs**
- Check if song is empty when chat starts
- Route to shaper agent vs orchestrator based on content

Recommend Option B for cleaner separation.

**Files to modify:**
- `api/routes/agents.py` - Add logic to choose agent based on song state
- `web/src/app/songs/[id]/page.tsx` - No changes needed (chat already there)
- `web/src/hooks/useChatSession.ts` or similar - May need to handle shaper events

### Phase 4: Update Metadata Panel

**File: `web/src/app/songs/[id]/components/` (wherever metadata panel lives)**

Add display for:
- Theme (from song notes)
- Key Images (from song notes)
- Emotional Arc (from song notes)

These should be editable so user can adjust context for AI.

### Phase 5: Remove Old Pages

**Delete or redirect:**
- `/songs/new/chat` page → redirect to `/songs/new`
- `/songs/new` page → simplify to just create song and redirect to editor
- Remove `SongShapeMindmap` component
- Remove `useSongShaper` hook (or repurpose)
- Remove `SongShapeService` (or keep for note storage)

### Phase 6: Update Prompt

**File: `api/agents/song_shaper.py`**

Update system prompt to reflect new capabilities:
- Mention it can CREATE sections (not just suggest)
- Explain that changes appear in the editor in real-time
- Guide user that they can also manually add/edit anytime

## Data Model Notes

### Song Notes for Shape Data
Use existing `SongNote` model with new `NoteType` values:
- `NoteType.THEME` - The song's theme/concept
- `NoteType.KEY_IMAGE` - Key images/phrases
- `NoteType.EMOTIONAL_ARC` - Start → Turning Point → End
- `NoteType.REFERENCE` - Reference songs/artists

Or use a single `NoteType.SONG_SHAPE` with structured JSON content.

### Section Intent
Store section intent in `SongSection.notes` field (already exists).

## Migration

For existing songs with shape data (`NoteType.SONG_SHAPE`):
- Could convert to sections on first load
- Or just leave as-is, new songs use new flow

## Success Criteria

1. User creates song → lands in editor immediately
2. Chat helps explore ideas (same great conversation)
3. When AI suggests structure and user confirms → sections appear in editor
4. Theme, images, arc visible in metadata panel
5. User can start writing lyrics immediately
6. No "Ready to Write" button needed - you're already writing

## Files Affected

### Backend
- `api/agents/song_shaper.py` - New tools, updated dependencies
- `api/routes/agents.py` - Route shaper for empty songs
- `api/services/song_shape.py` - May be removed or simplified
- `api/enums/note_type.py` - May add new note types

### Frontend
- `web/src/app/songs/new/page.tsx` - Simplify to create & redirect
- `web/src/app/songs/new/chat/page.tsx` - DELETE
- `web/src/components/shape/SongShapeMindmap.tsx` - DELETE
- `web/src/hooks/useSongShaper.ts` - DELETE or repurpose
- `web/src/app/songs/[id]/...` - Add shape data to metadata panel

## Notes from User

> "The chat is a great entry point that serves as a way of walking me through what I'm trying to create."

> "When I told it 'this is perfect' at the end, it should have created all these as data for my song and stored and organized it for me because IT knows how to."

> "I just want to see better what's being created from the chat."

The key insight: **The AI conversation is the onboarding/guided tour, and the song editor is the canvas. They should be together from the start.**
