# Vision: Style-Aware Co-Writing

> **Core Principle:** Completions that sound like YOU, not generic AI.

## The Problem with Generic AI

| Generic AI Tools | Result |
|------------------|--------|
| Trained on internet data | Sounds like everyone |
| Same model for all users | Generic, predictable voice |
| No memory of your work | Starts fresh every time |
| "AI slop" | You can tell it's AI |

## Greg's Approach: Your Style Library

Greg learns YOUR voice by retrieving from YOUR work—not by training a custom model, but by using your uploaded songs, progressions, and ideas as context for every suggestion.

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR STYLE LIBRARY                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  YOUR SONGS              YOUR PREFERENCES                   │
│  ├── finished_songs/     ├── chord_progressions_i_like.txt  │
│  ├── drafts/             ├── artists_i_admire.md            │
│  └── fragments/          └── themes_i_explore.md            │
│                                                              │
│  REFERENCE MATERIAL                                          │
│  ├── music_theory.pdf    ← Or use pre-trained knowledge     │
│  └── rhyme_dictionary/   ← Or use pre-trained knowledge     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     WHEN YOU WRITE...                        │
│                                                              │
│  "Walking through the rain, I can't help but think of—"     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  GREG RETRIEVES FROM YOUR WORK               │
│                                                              │
│  • Similar themes you've explored before                     │
│  • Your typical rhyme patterns and structures               │
│  • Chord progressions you gravitate toward                  │
│  • Vocabulary and phrasing that sounds like you             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   COMPLETION SOUNDS LIKE YOU                 │
│                                                              │
│  "Walking through the rain, I can't help but think of       │
│   all the ways we used to dance in storms like these"       │
│                                            ▲                 │
│                                            │                 │
│                        Informed by YOUR past work            │
└─────────────────────────────────────────────────────────────┘
```

## What Makes This Different

| Other AI Tools | Greg |
|----------------|------|
| Trained on the internet | Retrieves from YOUR library |
| Generic voice | YOUR voice |
| Same for everyone | Personal to you |
| Doesn't learn | Gets better as you add more songs |
| Forgets between sessions | Remembers your patterns |

## How It Works

### 1. Build Your Library

Upload your existing work:
- Finished songs (lyrics, chords, structure)
- Drafts and fragments (ideas you haven't finished)
- Chord progressions you love
- Themes and topics you explore

### 2. Greg Embeds Your Style

When you upload, Greg:
- Chunks your songs into meaningful pieces
- Creates embeddings (semantic fingerprints)
- Indexes for fast retrieval
- Learns patterns: rhyme schemes, themes, vocabulary

### 3. Style-Aware Completions

When you write, Greg:
- Retrieves relevant pieces from YOUR library
- Uses them as context for the LLM
- Generates completions that match YOUR voice
- The more you upload, the better it gets

## Knowledge Sources

| Source | How It's Used |
|--------|---------------|
| **Your Songs** | Primary style reference |
| **Your Preferences** | Chord progressions, themes, artists |
| **Pre-trained Models** | Music theory, rhyme patterns, general knowledge |
| **Mem0 (Future)** | Implicit learning from conversations |

**Note:** Music theory and general songwriting knowledge comes from pre-trained LLM capabilities. Your Style Library adds YOUR personal voice on top.

## Architecture Integration

The Style Library repurposes the existing RAG infrastructure:

```
┌─────────────────────────────────────────────────────────────┐
│                    EXISTING INFRASTRUCTURE                   │
│                                                              │
│  apps/writer/                                                │
│  ├── services/documents/   → Style Library upload           │
│  ├── services/vectorstore/ → Embedding storage              │
│  └── services/rag/         → Style retrieval                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SONGWRITER CO-WRITING                     │
│                                                              │
│  When generating:                                            │
│  1. Take user's current line/section                        │
│  2. Retrieve similar content from Style Library             │
│  3. Include retrieved context in LLM prompt                 │
│  4. Generate completion that sounds like the user           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Multi-Agent Integration

All agents in the multi-agent architecture should be style-aware:

| Agent | How It Uses Style Library |
|-------|---------------------------|
| **Songwriter** | Retrieves your patterns for completions |
| **Critic** | Compares new work to your established style |
| **Coach** | Identifies growth areas vs. your baseline |
| **Producer** | Suggests arrangements matching your preferences |

## The Virtuous Cycle

```
Upload more songs → Better style understanding → Better completions
       ↑                                               │
       └───────────────────────────────────────────────┘
                    You write more songs
```

## Key Insight

> **Greg doesn't try to make you sound like a "good songwriter."**
> **Greg tries to make you sound like the best version of YOU.**

Generic AI optimizes for average. Greg optimizes for YOUR voice.

---

## Related Documentation

- [Multi-Agent Architecture](../architecture/multi_agent.md) - How agents use style context
- [Mem0 Memory Layer](../integrations/mem0.md) - Future implicit learning
- [User Preferences System](../features/user_preferences.md) - Explicit preference settings
