# Songwriter App Roadmap

> **Primary Focus:** Style-aware co-writing platform

## Vision

A songwriter's creative partner that learns YOUR voice and helps you write better songs—not generic AI, but a tool that sounds like the best version of you.

See: [Style Library Vision](../product/vision.md)

---

## Current State

| Component | Status | Location |
|-----------|--------|----------|
| Song CRUD | Done | `api/` (new structure) |
| Section/Line models | Done | `api/` |
| Chord placement | Done | `api/` |
| Audio analysis (madmom) | Done | `api/` |
| Auth system | Done | `api/auth/` |
| User billing | In Progress | `api/` |
| Web frontend | In Progress | `web/` |
| Style Library (RAG) | Planned | Repurpose from Writer |

---

## Phase 1: Foundation

**Goal:** Solid base for multi-user songwriting

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 1.1 | Database persistence | Done | SQLAlchemy models |
| 1.2 | User authentication | Done | JWT + refresh tokens |
| 1.3 | Basic web UI | In Progress | Next.js in `web/` |
| 1.4 | Song CRUD in UI | In Progress | Create, view, edit, delete |
| 1.5 | Section editor | In Progress | Lyrics + chords |
| 1.6 | User billing/credits | In Progress | Stripe integration |
| 1.7 | Inline editing UX | Planned | Google Docs-style editing |
| 1.8 | Song list/dashboard | Planned | View all songs, search, filter |
| 1.9 | Duplicate song | Planned | Copy existing song as starting point |
| 1.10 | New song flow | Planned | Guided creation (title, key, tempo) |

See: [Inline Editor UX](../product/inline_editor_ux.md)

**Outcome:** Users can sign up, create songs, and manage their work.

---

## Phase 2: Style Library Integration

**Goal:** Personalized AI that learns your voice

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 2.1 | Song upload/import | Planned | Batch import existing songs |
| 2.2 | Style Library storage | Planned | Repurpose Writer RAG |
| 2.3 | Embedding pipeline | Planned | Chunk and embed user's songs |
| 2.4 | Style retrieval | Planned | Find similar patterns from library |

**Outcome:** Greg knows your songwriting patterns and preferences.

---

## Phase 3: AI Co-Writing

**Goal:** Real-time, style-aware completions

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 3.1 | `/complete` endpoint | Planned | Style-aware line completion |
| 3.2 | Ghost text UI | Planned | Tab to accept suggestions |
| 3.3 | Section suggestions | Planned | "Suggest a bridge" |
| 3.4 | Rhyme suggestions | Planned | Context-aware rhyme options |
| 3.5 | Chord suggestions | Planned | Based on your progressions |

**Outcome:** AI co-writes in YOUR voice, not generic AI voice.

---

## Phase 4: Feedback & Coaching

**Goal:** Multi-agent creative feedback

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 4.1 | Critic agent | Planned | Constructive feedback |
| 4.2 | Coach agent | Planned | Skill development |
| 4.3 | Producer agent | Planned | Arrangement suggestions |
| 4.4 | Feedback preferences | Planned | Adjust tone/depth |

See: [Multi-Agent Architecture](../architecture/multi_agent.md)

**Outcome:** Get personalized feedback that helps you grow.

---

## Phase 5: Export & Sharing

**Goal:** Get songs out of the app

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 5.1 | PDF chord sheets | Planned | WeasyPrint/ReportLab |
| 5.2 | Plain text export | Planned | Copy-pasteable format |
| 5.3 | Share read-only link | Planned | No login required |
| 5.4 | Stem separation | Planned | Demucs integration |
| 5.5 | Backing track generation | Planned | MusicGen integration |
| 5.6 | Demo generation | Planned | ElevenLabs API |

See: [Audio Generation Layer](../features/audio_generation.md)

**Outcome:** Share songs and generate reference tracks.

---

## Phase 6: Analytics & Growth

**Goal:** Understand your patterns

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 6.1 | Corpus analysis | Planned | "What progressions do I use?" |
| 6.2 | Writing streaks | Planned | Gamification |
| 6.3 | Progress tracking | Planned | Skills over time |
| 6.4 | Memory layer | Planned | Mem0 integration |

See: [Mem0 Memory Layer](../integrations/mem0.md)

**Outcome:** See your growth and patterns over time.

---

## Phase 7: Music Theory Helpers

**Goal:** Smart musical assistance

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 7.1 | Key detection from chords | Planned | "These chords are in G major" |
| 7.2 | Roman numeral analysis | Planned | I - V - vi - IV display |
| 7.3 | Chord suggestions | Planned | Fit the key/progression |
| 7.4 | Transposition | Planned | Change key, all chords update |
| 7.5 | Chord voicing hints | Planned | Common guitar voicings inline |
| 7.6 | Section relationships | Planned | Link Chorus 1 → Chorus 2 |

**Outcome:** AI understands music theory and helps users learn.

---

## Phase 8: Collaboration & Versioning

**Goal:** "Google Docs for songs"

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 8.1 | Real-time collaboration | Planned | WebSocket sync (CRDTs/Yjs) |
| 8.2 | Conflict resolution | Planned | Merge concurrent edits |
| 8.3 | Line comments/feedback | Planned | Comment on specific lines |
| 8.4 | Change history/audit log | Planned | Who changed what, when |
| 8.5 | Version history | Planned | See all changes over time |
| 8.6 | Version branching | Planned | "What if the bridge went differently?" |
| 8.7 | Version comparison | Planned | Diff view between versions |
| 8.8 | Version merging | Planned | Git for songs |

**Outcome:** Multiple songwriters jam remotely, experiment freely.

---

## Phase 9: Advanced Notation

**Goal:** Full musical notation support

| Priority | Feature | Status | Notes |
|----------|---------|--------|-------|
| 9.1 | Tab notation engine | Planned | Render guitar tabs |
| 9.2 | Fretboard input | Planned | Click fretboard to add notes |
| 9.3 | Tuning configurations | Planned | Standard, Drop D, DADGAD, etc. |
| 9.4 | Drum patterns | Planned | Beat library + notation |
| 9.5 | MIDI export | Planned | Export to DAW |
| 9.6 | MIDI playback | Planned | Hear progressions in-app |

See: [DAW Integration](../features/daw_integration.md)

**Outcome:** Full notation support for serious musicians.

---

## CLI Commands

Current:
```bash
uv run greg dev        # Start full stack (infra + API)
uv run greg server     # API only
uv run greg worker     # Background jobs
```

Planned:
```bash
uv run greg web        # Start Next.js frontend (port 3000)
```

Full stack development:
```bash
# Terminal 1 - Backend
uv run greg dev

# Terminal 2 - Frontend
uv run greg web
```

---

## Frontend Structure

```
web/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Home (song list)
│   │   ├── layout.tsx            # Root layout
│   │   └── songs/
│   │       ├── new/page.tsx      # Create song
│   │       └── [id]/page.tsx     # View/edit song
│   ├── components/
│   │   ├── SongCard.tsx          # Song list item
│   │   ├── SectionEditor.tsx     # Section editing
│   │   ├── ChordEditor.tsx       # Chord placement
│   │   └── StatusBadge.tsx       # Status indicator
│   ├── lib/
│   │   ├── api.ts                # API client
│   │   ├── songs.ts              # Song API functions
│   │   └── providers.tsx         # React Query
│   └── types/
│       └── song.ts               # TypeScript types
```

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| 1 | Users can create/edit songs | 100% functional |
| 2 | Style Library populated | User uploads 10+ songs |
| 3 | Completions feel personal | User says "sounds like me" |
| 4 | Feedback is actionable | User improves song |
| 5 | Demo sounds reasonable | Shareable quality |
| 6 | User returns weekly | Retention > 30% |

---

## Related Docs

- [Style Library Vision](../product/vision.md)
- [Multi-Agent Architecture](../architecture/multi_agent.md)
- [Audio Generation Layer](../features/audio_generation.md)
- [Mem0 Memory Layer](../integrations/mem0.md)
- [OpenRouter Integration](../integrations/openrouter.md)
- [DAW Integration](../features/daw_integration.md)
- [Inline Editor UX](../product/inline_editor_ux.md)
- [AI Interaction Modes](../product/ai_interaction_modes.md)
