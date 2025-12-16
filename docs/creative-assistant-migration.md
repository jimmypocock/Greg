# Greg: Creative Writing Assistant

A real-time creative writing assistant for songs and stories that learns YOUR style.

---

## Vision

**What we're building:** Copilot for creative writing that knows how YOU write - real-time suggestions informed by your own songs, stories, and references.

**The key insight:** Generic AI completions sound like AI. Completions informed by YOUR past work sound like YOU.

**What we're NOT building:** A chat interface or another generic AI writing tool.

### Core Experience

```
┌─────────────────────────────────────────────────────────────────┐
│  📝 Untitled Song                                    [⚙️] [💾]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Verse 1]                                                      │
│  Walking through the rain at midnight                           │
│  Thinking 'bout the words I never said                          │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░                         │
│  ← "Now I'm drowning in the silence instead" (Tab to accept)    │
│                                                                 │
│  [Chorus]                                                       │
│  _                                                              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  💡 SUGGESTIONS                          📊 STRUCTURE           │
│  ─────────────────────────────           ─────────────────────  │
│  Rhymes with "said":                     ✓ Verse 1 (complete)   │
│  • head, bed, led, dead, spread          ○ Chorus (empty)       │
│                                          ○ Verse 2              │
│  Your theme "regret" fits well           ○ Bridge               │
│  with introspection here                 ○ Final Chorus         │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  🎯 CONTEXT                                                     │
│  Theme: regret, missed opportunities     Tone: melancholic      │
│  Style: folk ballad                      Tempo: slow            │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Ghost text completion** | See suggestions inline, Tab to accept |
| **Structure tracking** | Know where you are (verse, chorus, act, scene) |
| **Context awareness** | Suggestions match your themes, characters, tone |
| **Rhyme/rhythm helpers** | For songs: rhyme suggestions, syllable counts |
| **Optional, not intrusive** | Toggle suggestions on/off, adjust aggressiveness |

---

## What We Keep from Greg

Greg has solid infrastructure. Almost everything transfers - we're ADDING features, not removing.

### ✅ Keep As-Is

| Component | Location | Why Keep |
|-----------|----------|----------|
| **FastAPI structure** | `src/api/` | Clean patterns, middleware, CORS |
| **Authentication** | `src/auth/` | Users, JWT, sessions, API keys |
| **Database setup** | `src/database/` | PostgreSQL, Alembic migrations |
| **Background jobs** | `src/jobs/` | ARQ + Redis for async tasks |
| **WebSocket manager** | `src/websocket/` | Real-time streaming |
| **Cost tracking** | `src/costs/` | Track LLM usage per user |
| **LLM providers** | `src/llm/` | Ollama, Claude, OpenAI abstraction |
| **Config/settings** | `src/config/` | Environment management |
| **Security** | `src/security/` | Input sanitization |
| **Document upload** | `src/api/routes/` | Upload songs, references |
| **Document processing** | `src/jobs/` | PDF/text chunking |
| **pgvector embeddings** | `src/database/` | Semantic search YOUR style |
| **RAG retrieval** | `src/rag/` | Find similar patterns in YOUR work |

### 🔄 Repurpose

| From | To |
|------|-----|
| `/ask` endpoint | `/complete` endpoint (style-aware completions) |
| `/documents` | `/library` (your songs, references, style docs) |
| RAG retrieval | Style matching (find similar lines YOU wrote) |
| Document chunks | Style fragments (your patterns, themes, phrases) |
| WebSocket for job progress | WebSocket for live completions |

### ➕ Add New

| Component | Purpose |
|-----------|---------|
| `/projects` | Active songs/stories you're writing |
| `/complete` | Real-time streaming completions |
| Context system | Themes, characters, tone per project |
| Structure analysis | Song sections, story beats |
| Next.js frontend | Editor with ghost text |

---

## Style Library: RAG for YOUR Voice

The key feature that makes Greg different from generic AI writing tools.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  1. UPLOAD YOUR WORK                                            │
│  ────────────────────                                           │
│  📄 my_songs_2020_2024.pdf     → Chunked, embedded, indexed     │
│  📄 favorite_chord_progs.txt  → Chunked, embedded, indexed     │
│  📄 story_drafts.docx         → Chunked, embedded, indexed     │
│                                                                 │
│  Greg now has YOUR patterns, YOUR themes, YOUR voice            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. YOU START WRITING                                           │
│  ────────────────────                                           │
│  "The midnight train pulls away                                 │
│   Leaving nothing but the rain_"                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. GREG RETRIEVES FROM YOUR LIBRARY                            │
│  ────────────────────────────────────                           │
│  Found similar patterns in YOUR songs:                          │
│  • "The last bus home, empty seats and cigarette smoke"         │
│  • "Standing on the platform, watching you disappear"           │
│  • "Rain on the window, memories on repeat"                     │
│                                                                 │
│  Your themes: departure, loneliness, rain imagery               │
│  Your patterns: 8-syllable lines, ABAB rhyme scheme             │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. STYLE-AWARE COMPLETION                                      │
│  ──────────────────────────                                     │
│  Suggestion: "And I'm drowning in yesterday"                    │
│                                                                 │
│  Why this works:                                                │
│  • Matches your syllable pattern (8 syllables)                  │
│  • Rhymes with "away" (your typical ABAB)                       │
│  • Uses water imagery (common in your work)                     │
│  • Melancholic tone (your style)                                │
└─────────────────────────────────────────────────────────────────┘
```

### Library Categories

| Category | What to Upload | How Greg Uses It |
|----------|----------------|------------------|
| **Your songs** | Lyrics, chord sheets | Learn your voice, patterns, themes |
| **Your stories** | Drafts, finished work | Character voice, pacing, style |
| **References** | Music theory, craft books | Technical knowledge |
| **Inspirations** | Songs/stories you love | Understand your influences |

### Completion Flow with RAG

```python
async def get_style_aware_completion(
    current_text: str,
    project_context: dict,
    user_id: str
) -> Completion:
    # 1. Retrieve similar passages from USER's library
    similar_chunks = await rag_service.retrieve(
        query=current_text[-200:],  # Recent context
        user_id=user_id,            # Only THEIR documents
        max_chunks=5
    )

    # 2. Extract style patterns
    style_context = extract_patterns(similar_chunks)
    # - rhyme schemes used
    # - syllable patterns
    # - common themes
    # - vocabulary preferences

    # 3. Build style-aware prompt
    prompt = build_completion_prompt(
        current_text=current_text,
        project_context=project_context,
        style_examples=similar_chunks,
        style_patterns=style_context
    )

    # 4. Generate completion
    return await llm.complete(prompt)
```

---

## New Architecture

### Database Schema

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     users       │     │    projects     │     │    contexts     │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id              │────<│ id              │────<│ id              │
│ email           │     │ user_id (FK)    │     │ project_id (FK) │
│ hashed_password │     │ title           │     │ key             │
│ ...             │     │ type (song/     │     │ value           │
└─────────────────┘     │      story)     │     │ type (theme/    │
                        │ content (text)  │     │   character/    │
                        │ structure_type  │     │   tone/etc)     │
                        │ created_at      │     └─────────────────┘
                        │ updated_at      │
                        └─────────────────┘
                               │
                               │
                        ┌──────▼──────────┐
                        │   completions   │
                        ├─────────────────┤
                        │ id              │
                        │ project_id (FK) │
                        │ prompt          │
                        │ completion      │
                        │ accepted (bool) │
                        │ position        │
                        │ created_at      │
                        └─────────────────┘
```

### New Models

```python
# src/database/models/project.py

class ProjectType(str, Enum):
    SONG = "song"
    STORY = "story"

class StructureType(str, Enum):
    # Songs
    VERSE_CHORUS = "verse_chorus"
    AABA = "aaba"
    FREEFORM = "freeform"
    # Stories
    THREE_ACT = "three_act"
    HEROS_JOURNEY = "heros_journey"
    FREEFORM_STORY = "freeform_story"

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    type: Mapped[ProjectType]
    structure_type: Mapped[StructureType]
    content: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(onupdate=func.now())

    # Relationships
    contexts: Mapped[list["Context"]] = relationship(back_populates="project")
    completions: Mapped[list["Completion"]] = relationship(back_populates="project")


class Context(Base):
    __tablename__ = "contexts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    key: Mapped[str]  # "theme", "character", "tone", "style"
    value: Mapped[str]  # "regret", "Jack - retired detective", "melancholic"

    project: Mapped["Project"] = relationship(back_populates="contexts")
```

### API Endpoints

```
# Projects
POST   /projects              Create new song/story
GET    /projects              List user's projects
GET    /projects/{id}         Get project with content
PATCH  /projects/{id}         Update content/title
DELETE /projects/{id}         Delete project

# Context
POST   /projects/{id}/context       Add theme/character/tone
GET    /projects/{id}/context       Get all context
DELETE /projects/{id}/context/{key} Remove context item

# Completions (the magic)
POST   /complete                    Get completion suggestions
WS     /ws/complete                 Real-time streaming completions

# Structure helpers
GET    /structure/songs             Available song structures
GET    /structure/stories           Available story structures
POST   /analyze/structure           Analyze current content structure
POST   /analyze/rhymes              Get rhyme suggestions (songs)
```

### Completion Request/Response

```python
# Request
{
    "project_id": "uuid",
    "content": "Walking through the rain at midnight\nThinking bout the words I never said\n",
    "cursor_position": 67,  # Where the cursor is
    "context": {
        "themes": ["regret", "missed opportunities"],
        "tone": "melancholic",
        "style": "folk ballad"
    },
    "structure_hint": "verse_1",  # Where we are in structure
    "max_tokens": 50,
    "temperature": 0.8
}

# Response (streaming)
{
    "completion": "Now I'm drowning in the silence instead",
    "confidence": 0.85,
    "alternatives": [
        "But your memory lives inside my head",
        "Wishing I could take it back instead"
    ],
    "rhyme_info": {
        "rhymes_with": "said",
        "syllables": 10
    }
}
```

---

## Frontend: Next.js App

### Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Framework** | Next.js 14 (App Router) | React + SSR + API routes |
| **Editor** | Monaco Editor or Tiptap | Rich text + custom extensions |
| **Styling** | Tailwind CSS | Fast, utility-first |
| **State** | Zustand or Jotai | Simple, performant |
| **Real-time** | Native WebSocket | Stream completions |

### Key Components

```
frontend/
├── app/
│   ├── page.tsx                 # Landing/dashboard
│   ├── editor/[id]/page.tsx     # Main editor view
│   ├── projects/page.tsx        # Project list
│   └── api/                     # API route proxies (optional)
├── components/
│   ├── Editor/
│   │   ├── Editor.tsx           # Main editor wrapper
│   │   ├── GhostText.tsx        # Inline suggestions
│   │   ├── CompletionProvider.tsx
│   │   └── hooks/
│   │       ├── useCompletion.ts # Fetch completions
│   │       └── useDebounce.ts   # Debounce typing
│   ├── Sidebar/
│   │   ├── ContextPanel.tsx     # Themes, characters
│   │   ├── StructurePanel.tsx   # Song/story structure
│   │   └── SuggestionsPanel.tsx # Rhymes, alternatives
│   └── ui/                      # Shared components
├── lib/
│   ├── api.ts                   # API client
│   ├── websocket.ts             # WebSocket manager
│   └── completions.ts           # Completion logic
└── stores/
    ├── editor.ts                # Editor state
    └── project.ts               # Current project
```

### Ghost Text Implementation

```typescript
// Simplified ghost text logic
function useGhostText(content: string, cursorPosition: number) {
  const [ghostText, setGhostText] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Debounce: wait for user to stop typing
  const debouncedContent = useDebounce(content, 500);

  useEffect(() => {
    if (!debouncedContent) return;

    const fetchCompletion = async () => {
      setIsLoading(true);
      const completion = await getCompletion({
        content: debouncedContent,
        cursor_position: cursorPosition,
      });
      setGhostText(completion.text);
      setIsLoading(false);
    };

    fetchCompletion();
  }, [debouncedContent, cursorPosition]);

  const acceptCompletion = () => {
    // Insert ghost text at cursor
    insertText(ghostText);
    setGhostText("");
  };

  return { ghostText, isLoading, acceptCompletion };
}
```

---

## Migration Plan

### Phase 1: Backend Restructure (Keep Greg Running)

1. **Create new models** - Project, Context, Completion
2. **Add migrations** - New tables alongside existing
3. **Create completion service** - New `src/completion/` module
4. **Add new endpoints** - `/projects`, `/complete`
5. **Keep existing endpoints** - Greg still works during migration

```bash
# New files to create
src/
├── completion/
│   ├── __init__.py
│   ├── service.py        # Completion logic
│   ├── prompts.py        # Prompt templates
│   └── schemas.py        # Request/response models
├── projects/
│   ├── __init__.py
│   ├── service.py        # CRUD operations
│   └── schemas.py
└── api/routes/
    ├── projects.py       # Project endpoints
    └── complete.py       # Completion endpoints
```

### Phase 2: Frontend (New Next.js App)

1. **Scaffold Next.js app** - In new `frontend/` directory
2. **Build editor component** - Monaco or Tiptap
3. **Implement ghost text** - Tab to accept
4. **Add context panel** - Themes, characters, tone
5. **Connect to backend** - API calls + WebSocket

### Phase 3: Polish & Remove Old Code

1. **Remove RAG components** - `src/rag/`, `src/ask/`
2. **Remove document processing** - Chunking, embeddings
3. **Drop unused tables** - `documents`, `document_chunks`
4. **Rename project** - Greg → Muse? Quill? Your call

---

## Prompt Engineering

The quality of suggestions depends heavily on prompts.

### Song Completion Prompt

```python
SONG_COMPLETION_PROMPT = """You are a songwriting assistant. Complete the next line of this song.

Context:
- Theme: {themes}
- Tone: {tone}
- Style: {style}
- Current section: {structure_hint}

Song so far:
{content}

Requirements:
- Match the established rhythm and syllable pattern
- If the previous line ends with a rhyme scheme, continue it
- Stay true to the theme and tone
- Keep it natural, not forced

Complete the next line (just the line, no explanation):"""
```

### Story Completion Prompt

```python
STORY_COMPLETION_PROMPT = """You are a fiction writing assistant. Continue this story naturally.

Context:
- Genre: {genre}
- Tone: {tone}
- Characters: {characters}
- Current scene: {structure_hint}

Story so far:
{content}

Requirements:
- Match the author's voice and style
- Maintain character consistency
- Keep the pacing appropriate for this point in the story
- Don't be generic - be specific and vivid

Continue naturally (1-2 sentences):"""
```

---

## Performance Considerations

### Latency Budget

For real-time feel, completions need to appear within **200-500ms**.

| Component | Target | Notes |
|-----------|--------|-------|
| Debounce | 300-500ms | Wait for typing pause |
| API round-trip | 50ms | Local backend |
| LLM generation | 100-300ms | Streaming helps |
| Render | <16ms | 60fps |

### Strategies

1. **Stream completions** - Show text as it generates
2. **Speculative execution** - Pre-fetch likely completions
3. **Local model option** - Ollama for lowest latency
4. **Caching** - Cache common patterns/rhymes
5. **Shorter outputs** - 1-2 lines max per suggestion

---

## What's Different from Existing Tools

| Tool | Gap | Our Advantage |
|------|-----|---------------|
| ChatGPT | Chat-based, not in-document | Real-time ghost text |
| Sudowrite | Expensive, web-only | Local-first, your data |
| Notion AI | Generic, not creative-focused | Built for songs/stories |
| GitHub Copilot | Code-focused | Creative writing focused |

---

## Open Questions

1. **Name?** - Greg doesn't fit anymore. Muse? Quill? Verse?
2. **Monetization?** - Free tier + paid? One-time?
3. **Desktop app?** - Electron wrapper for offline?
4. **Collaboration?** - Multi-user editing eventually?
5. **Export?** - PDF, Word, chord sheets?

---

## Next Steps

1. [ ] Decide on project name
2. [ ] Create new database models + migrations
3. [ ] Build `/complete` endpoint with streaming
4. [ ] Scaffold Next.js frontend
5. [ ] Implement basic editor with ghost text
6. [ ] Add context/theme management
7. [ ] Build structure analysis for songs
8. [ ] Polish and iterate

---

## Resources

- [Monaco Editor](https://microsoft.github.io/monaco-editor/) - VS Code's editor
- [Tiptap](https://tiptap.dev/) - Headless rich text editor
- [Vercel AI SDK](https://sdk.vercel.ai/) - Streaming UI helpers
- [Ollama](https://ollama.ai/) - Local LLMs
