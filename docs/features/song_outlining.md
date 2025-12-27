# Song Outlining & Visualization System

> **Status:** Planned (Future Feature)
> **Priority:** Medium-term
> **Inspiration:** Screenplay outlining tools (index cards, mind maps, beat sheets, emotional arc plotters)

## Overview

A suite of visual tools to help songwriters plan, structure, and analyze their songs. Inspired by professional screenwriting tools that help writers visualize narrative structure and emotional pacing.

## Feature Set

### 1. Section Cards View (Kanban-Style)

A visual, drag-and-drop interface for song structure.

**Functionality:**
- Each section (verse, chorus, bridge, etc.) displayed as a card
- Drag to reorder song structure
- Color-coded by section type
- Expandable to show lyrics preview
- Quick stats on each card (line count, chord progression, estimated duration)

**Card Display:**
```
┌────────────────────┐
│ 🟦 Verse 1         │
│ ─────────────────  │
│ Am → C → G → F     │
│ 8 lines · ~45 sec  │
│ ─────────────────  │
│ "Walking down the  │
│  empty street..."  │
└────────────────────┘
```

**Color Coding:**
- 🟦 Blue: Verse
- 🟨 Yellow: Chorus
- 🟩 Green: Bridge
- 🟪 Purple: Pre-chorus
- ⬜ Gray: Intro/Outro
- 🟧 Orange: Instrumental

**Interactions:**
- Drag cards to reorder
- Click to expand/edit
- Double-click to jump to section in editor
- Right-click for options (duplicate, delete, add notes)

**Use Cases:**
- Quickly try different song structures (ABABCB vs AABABCB)
- See the big picture of a song at a glance
- Identify structural imbalances (too many verses, no bridge)

---

### 2. Emotional Arc Visualization

A graph showing the emotional intensity/energy throughout the song.

**Functionality:**
- X-axis: Song timeline (sections)
- Y-axis: Emotional intensity (0-100)
- AI-analyzed or user-defined intensity per section
- Overlay common song arc templates for comparison

**Visualization:**
```
Intensity
100 │                    ┌───┐
    │              ┌───┐ │   │ ┌───┐
 75 │        ┌───┐ │   │ │   │ │   │
    │   ┌──┐ │   │ │   │ │   │ │   │
 50 │ ──┤  ├─┤   ├─┤   ├─┘   └─┤   │
    │   │  │ │   │ │   │       │   │
 25 │   │  │ │   │ │   │       │   └──
    │   └──┘ └───┘ └───┘       └──────
  0 └─────────────────────────────────→
      Intro V1   Ch   V2   Ch   Br  Ch  Outro
```

**AI Analysis Factors:**
- Lyrical intensity (word choice, imagery)
- Melodic density (notes per bar)
- Harmonic tension (chord complexity, key changes)
- Dynamic markings (if provided)
- Syllable density per line

**Template Overlays:**
- "The Climb" - Steady build to final chorus
- "Rollercoaster" - Multiple peaks and valleys
- "Slow Burn" - Low verses, explosive choruses
- "Bookend" - Strong open, quiet middle, strong close

**Use Cases:**
- Identify flat sections that need more energy
- Ensure chorus lifts above verses
- Plan intentional dynamics before writing

---

### 3. Concept Mind Map

A brainstorming canvas for developing song themes and lyrics.

**Functionality:**
- Central node: Main theme/concept
- Branch nodes: Sub-themes, emotions, imagery
- Leaf nodes: Specific lyric ideas, phrases, rhymes
- Connect related ideas across branches
- Drag lyrics from map into song sections

**Example Structure:**
```
                        ┌─ "counting stars alone"
           ┌─ Solitude ─┼─ "empty side of bed"
           │            └─ "table set for one"
           │
           │            ┌─ "your voice echoes"
Theme: ────┼─ Memories ─┼─ "photographs fade"
Missing    │            └─ "songs we used to sing"
You        │
           │            ┌─ "learning to breathe"
           └─ Healing ──┼─ "sun still rises"
                        └─ "carry you forward"
```

**Features:**
- Auto-suggest related concepts (AI-powered)
- Rhyme suggestions for selected words
- Color-code by emotion (sad=blue, hopeful=yellow)
- Mark ideas as "used" when pulled into lyrics
- Save maps as templates for future songs

**Interactions:**
- Double-click to create node
- Drag to connect nodes
- Right-click for AI suggestions
- Drag node to section editor to use phrase

---

### 4. Beat Sheet / Song Outline

A simple, linear outline for planning before writing.

**Functionality:**
- Ordered list of sections with purpose annotations
- Define what each section should accomplish emotionally/narratively
- Checklist to track completion
- AI can generate outline from concept/theme

**Example:**
```markdown
## Song: "Empty Chair"
**Theme:** Grief and gradual acceptance after loss
**Target Length:** 3:30

### Structure

1. [ ] **Intro** (8 bars)
   - Mood: Quiet, contemplative
   - Sparse piano, set the tone

2. [ ] **Verse 1**
   - Establish the absence
   - Concrete imagery: empty chair, cold coffee
   - End with question or longing

3. [ ] **Pre-Chorus**
   - Build tension
   - Transition from observation to emotion

4. [ ] **Chorus**
   - Core emotional statement
   - Melodic peak
   - Hook: "I still set the table for two"

5. [ ] **Verse 2**
   - Deeper into memories
   - More vulnerable than V1
   - Show passage of time

6. [ ] **Chorus**

7. [ ] **Bridge**
   - Shift perspective
   - Turning point: acceptance begins
   - Musical contrast (key change?)

8. [ ] **Final Chorus**
   - Variation on chorus
   - Resolution or open-ended

9. [ ] **Outro**
   - Echo intro motif
   - Fade or definitive end
```

**AI Features:**
- Generate outline from theme/concept
- Suggest section purposes based on genre
- Flag missing common elements (no bridge? no pre-chorus?)

---

### 5. Structure Templates Library

Pre-built song structures users can start from.

**Template Categories:**

**Pop:**
- Verse-Chorus-Verse-Chorus-Bridge-Chorus (ABABCB)
- Verse-PreChorus-Chorus-Verse-PreChorus-Chorus-Bridge-Chorus

**Rock:**
- Intro-Verse-Verse-Chorus-Verse-Chorus-Solo-Chorus-Outro

**Ballad:**
- Intro-Verse-Chorus-Verse-Chorus-Bridge-Chorus-Outro (slow build)

**Folk/Storytelling:**
- Verse-Verse-Verse-Chorus-Verse-Chorus (narrative focus)

**Hip-Hop:**
- Intro-Verse-Hook-Verse-Hook-Verse-Hook-Outro

**Each Template Includes:**
- Section order
- Suggested bar counts
- Emotional arc overlay
- Example songs using this structure

---

## Database Schema

```sql
-- Song outlines/beat sheets
CREATE TABLE song_outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    song_id UUID REFERENCES songs(id) ON DELETE CASCADE,
    sections JSONB NOT NULL DEFAULT '[]',
    -- [{order: 1, type: "verse", purpose: "...", completed: false}, ...]
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mind maps
CREATE TABLE song_mind_maps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    song_id UUID REFERENCES songs(id) ON DELETE CASCADE,
    nodes JSONB NOT NULL DEFAULT '[]',
    -- [{id, label, parent_id, position: {x, y}, color, used: false}, ...]
    edges JSONB NOT NULL DEFAULT '[]',
    -- [{source_id, target_id}, ...]
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Emotional arc data (can be AI-generated or user-defined)
CREATE TABLE song_emotional_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    song_id UUID REFERENCES songs(id) ON DELETE CASCADE,
    data_points JSONB NOT NULL DEFAULT '[]',
    -- [{section_id, intensity: 0-100, notes: "..."}, ...]
    ai_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Structure templates (system + user-created)
CREATE TABLE structure_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE, -- NULL for system templates
    name VARCHAR(100) NOT NULL,
    genre VARCHAR(50),
    sections JSONB NOT NULL,
    emotional_arc JSONB,
    example_songs TEXT[],
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API Endpoints

```
# Section Cards
GET    /songs/{id}/structure          - Get section cards
PUT    /songs/{id}/structure          - Update section order
POST   /songs/{id}/structure/reorder  - Bulk reorder sections

# Mind Maps
GET    /songs/{id}/mind-map           - Get mind map
PUT    /songs/{id}/mind-map           - Update mind map
POST   /songs/{id}/mind-map/suggest   - AI suggestions for node

# Emotional Arc
GET    /songs/{id}/emotional-arc      - Get arc data
PUT    /songs/{id}/emotional-arc      - Update arc (user-defined)
POST   /songs/{id}/emotional-arc/analyze - AI analysis

# Beat Sheets
GET    /songs/{id}/outline            - Get outline
PUT    /songs/{id}/outline            - Update outline
POST   /songs/{id}/outline/generate   - AI generate from theme

# Templates
GET    /templates                     - List templates
GET    /templates/{id}                - Get template
POST   /templates                     - Create user template
POST   /songs/{id}/apply-template     - Apply template to song
```

---

## Frontend Components

### Section Cards View
- React DnD or dnd-kit for drag-and-drop
- Framer Motion for smooth animations
- Collapsible cards with lyrics preview

### Emotional Arc Chart
- Recharts or D3.js for visualization
- Interactive: click to edit intensity
- Overlay toggle for template comparison

### Mind Map Canvas
- React Flow for node-based canvas
- Auto-layout with dagre
- Minimap for navigation

### Beat Sheet Editor
- Markdown-style editor
- Checkbox tracking
- Collapsible sections

---

## AI Integration

### Emotional Arc Analysis
```python
async def analyze_emotional_arc(song: Song) -> list[ArcDataPoint]:
    """
    Analyze song sections and estimate emotional intensity.

    Factors:
    - Word sentiment and intensity
    - Syllable density (busier = more intense)
    - Chord tension (minor, diminished, 7ths)
    - Section type (chorus typically higher)
    - Line length variation
    """
    ...
```

### Mind Map Suggestions
```python
async def suggest_mind_map_nodes(
    theme: str,
    existing_nodes: list[Node]
) -> list[SuggestedNode]:
    """
    Given a theme and existing brainstorm, suggest related:
    - Sub-themes
    - Imagery/metaphors
    - Concrete details
    - Rhyming phrases
    """
    ...
```

### Outline Generation
```python
async def generate_outline(
    theme: str,
    genre: str,
    mood: str,
    target_length: str
) -> SongOutline:
    """
    Generate a beat sheet / song outline from a concept.
    """
    ...
```

---

## Implementation Phases

### Phase 1: Section Cards
- Visual section overview
- Drag-and-drop reordering
- Basic card info (type, line count, chords)

### Phase 2: Beat Sheet
- Outline editor
- Section purpose annotations
- AI outline generation

### Phase 3: Emotional Arc
- Manual intensity input per section
- Basic visualization
- Template overlays

### Phase 4: AI Arc Analysis
- Automatic intensity estimation
- Suggestions for improvement
- "Your chorus doesn't lift" warnings

### Phase 5: Mind Map
- Full canvas brainstorming
- AI suggestions
- Drag-to-editor integration

---

## Success Metrics

- Users who use outlining tools complete more songs
- Time from concept to finished draft decreases
- AI arc suggestions lead to structural revisions
- Template usage by new users (onboarding value)

---

## References

- [No Film School: Screenplay Outlining Tools](https://nofilmschool.com/ultimate-guide-screenplay-outlining-tools)
- Save the Cat beat sheet methodology
- Song structure analysis from Hooktheory
