# Competitive Analysis

> **Where competitors fall short—and where Greg wins.**

## Landscape

| Competitor | Focus | Gap |
|------------|-------|-----|
| **LyricStudio** | Lyrics + rhymes | No critique, generic voice |
| **Jarvis Lyrics** | Multi-language generation | No critique, no learning |
| **Hookpad** | Chords + theory | Strong incumbent, no lyrics |
| **Staccato** | DAW co-writing | Production focus, no feedback |

---

## Common Gaps Across All Competitors

1. **No personalized voice** - Generic AI that sounds the same for everyone
2. **No critique/feedback** - Generate but don't improve
3. **Lyrics OR chords** - Not unified songwriting
4. **No learning over time** - Each session starts fresh

---

## Greg's Differentiators

### 1. Style Library (Personal Voice)

**Competitor approach:** Train on the internet, output generic suggestions.

**Greg's approach:** Retrieve from YOUR songs, sound like YOU.

```
Competitor:  "Here's what AI thinks a love song sounds like"
Greg:        "Here's what YOUR love songs sound like—continue from here"
```

**Cost:** Retrieval is cheap (vector search), no fine-tuning needed.

**Power:** The more you use it, the better it gets. Sticky.

---

### 2. Multi-Agent Critique

**Competitor approach:** Generate lyrics, done.

**Greg's approach:** Generate, then critique, then refine.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Draft     │ ──► │   Critique  │ ──► │   Polish    │
│   (Lyricist)│     │   (Critic)  │     │   (Lyricist)│
└─────────────┘     └─────────────┘     └─────────────┘
```

**Gap exploited:** LyricStudio, Jarvis, Staccato all generate without feedback.

**Cost:** 2-3x tokens per generation, but quality >> quantity.

**Power:** Users improve as writers, not just as users.

---

### 3. Unified Lyrics + Chords

**Competitor approach:**
- LyricStudio: Lyrics only
- Hookpad: Chords only
- Neither: Both together

**Greg's approach:** Lyrics and chords in one editor, analyzed together.

```
     G        C         D
This is the first line of the verse
     Em       C
Second line with the chord progression
```

**Gap exploited:** Hookpad is strong on theory but doesn't touch lyrics.

**Cost:** Same infrastructure, just unified UI.

**Power:** Songwriters don't think in "lyrics" vs "chords"—they think in songs.

---

### 4. Four Interaction Modes

**Competitor approach:** One way to interact (usually "generate on demand").

**Greg's approach:** Four modes for different creative states:

| Mode | When to Use | Competitor Equivalent |
|------|-------------|----------------------|
| **Completion** | Active writing, need a line | LyricStudio's core |
| **Session** | Brainstorming, exploring | None |
| **Autopilot** | Stuck, need full section | None |
| **Ambient** | Flow state, don't interrupt | None |

**Gap exploited:** Competitors are one-trick ponies.

**Power:** Meet users where they are creatively.

---

### 5. Audio → Song

**Competitor approach:** Start from blank page or text.

**Greg's approach:** Upload reference track, extract:
- Tempo
- Key
- Time signature
- Chord progression

```
User uploads: favorite_song.mp3
Greg extracts: 120 BPM, G major, 4/4, I-V-vi-IV
User starts: Already in the right key/feel
```

**Gap exploited:** No competitor starts from audio.

**Cost:** Open source tools (librosa, madmom), runs on CPU.

**Power:** Lower barrier to start, learn from references.

---

## Borrowed Concepts, Uniquely Applied

### From Hookpad: Theory Visualization

**What Hookpad does:** Roman numeral analysis, chord function colors.

**How Greg applies it:**
- Show I-V-vi-IV notation optionally
- But applied to USER'S chord progressions
- Combined with lyrics (Hookpad doesn't do this)
- AI suggests "this borrows from parallel minor" (contextual learning)

**Unique twist:** Theory as feedback, not just display.

---

### From LyricStudio: Rhyme Suggestions

**What LyricStudio does:** Rhyme database, syllable matching.

**How Greg applies it:**
- Same functionality (rhyme lookup)
- But filtered through Style Library ("rhymes YOU use")
- Combined with ambient mode (appear as you type, non-blocking)
- Critic evaluates rhyme quality ("too cliché?")

**Unique twist:** Personal rhyme preferences, not just dictionary.

---

### From Staccato: DAW Integration

**What Staccato does:** Live in the DAW, co-write during production.

**How Greg applies it:**
- OSC bridge to Ableton Live
- But bidirectional: DAW → Greg analysis, Greg → DAW export
- Chord progression from Greg → MIDI clip in DAW
- Audio from DAW → tempo/key detection in Greg

**Unique twist:** Not DAW-native (less lock-in), but fully integrated.

---

### From Google Docs: Real-time Collaboration

**What Google Docs does:** Multiple cursors, live sync, comments.

**How Greg applies it:**
- Yjs/CRDTs for conflict resolution
- Line-level comments for feedback
- But specialized for songs (section awareness, chord conflicts)
- Version branching ("what if the bridge went differently?")

**Unique twist:** Git for songs, not just Google Docs for text.

---

## Cost-Effective Strategies

| Strategy | Cost | Impact |
|----------|------|--------|
| **Style Library (RAG)** | Vector DB + embeddings | High - core differentiator |
| **Multi-agent critique** | 2-3x tokens | High - quality over quantity |
| **Rhyme/theory tools** | Free APIs + open source | Medium - table stakes |
| **Audio analysis** | CPU-only, open source | Medium - unique onramp |
| **Real-time collab** | Yjs (open source) | Medium - stickiness |
| **DAW integration** | OSC (free protocol) | Low initially - power users |

---

## Positioning Statement

> **Greg is the only AI songwriting tool that learns YOUR voice, critiques YOUR work, and helps YOU grow as a writer—not just generates generic lyrics.**

vs. LyricStudio: "We critique, they just generate"
vs. Hookpad: "We do lyrics too, and learn your style"
vs. Staccato: "We're not locked to a DAW, and we give feedback"

---

## Competitive Moats

1. **Style Library depth** - More songs = better suggestions = harder to leave
2. **Writing history** - Your growth over time, tracked
3. **Agent feedback quality** - Critique that actually helps (tuned prompts)
4. **Unified experience** - Lyrics + chords + audio + collaboration

---

## Anti-Goals

Things Greg intentionally **doesn't** compete on:

| Area | Why Not |
|------|---------|
| **Full DAW replacement** | Staccato's lane, we integrate instead |
| **Music production** | MusicGen/Suno's lane, we focus on songwriting |
| **Sheet music notation** | Hookpad's strength, we do chord charts |
| **Vocal synthesis** | ElevenLabs/Suno's lane, we export to them |

---

## Related Documentation

- [Vision: Style Library](./vision.md) - Core differentiator
- [Multi-Agent Architecture](../architecture/multi_agent.md) - Critique system
- [AI Interaction Modes](./ai_interaction_modes.md) - Four modes
- [DAW Integration](../features/daw_integration.md) - Ableton bridge
- [Audio Analysis](../features/audio_analysis.md) - Reference track extraction
