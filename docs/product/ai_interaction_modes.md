# AI Interaction Modes

> **Four ways to collaborate with Greg—from gentle nudges to full autopilot.**

## Overview

| Mode | User Action | AI Behavior | Best For |
|------|-------------|-------------|----------|
| **Completion** | Requests suggestion | Suggests next line | Active writing sessions |
| **Session** | Explores ideas | Organizes into structure | Starting from scratch, brainstorming |
| **Autopilot** | Delegates task | Drives with checkpoints | Getting unstuck, filling gaps |
| **Ambient** | Just writes | Proactively offers alternatives | Flow state, refinement |

---

## 1. Completion Mode

**"Suggest the next line"**

The most direct interaction. User explicitly asks for help, AI responds with a suggestion.

### How It Works

```
User writes:    "Walking through the rain, I can't help but think of—"
User action:    Clicks "Suggest" or presses Tab
AI suggests:    "all the ways we used to dance in storms like these"
User:           Accepts, rejects, or modifies
```

### UI Concepts

- **Ghost text**: Grayed-out suggestion that appears inline (Tab to accept)
- **Suggestion panel**: Multiple options ranked by style match
- **Keyboard shortcuts**:
  - `Tab` - Accept suggestion
  - `Esc` - Dismiss
  - `Ctrl+Space` - Request suggestion

### Technical Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User requests  │ ──▶ │  Retrieve from   │ ──▶ │  Generate with  │
│  completion     │     │  Style Library   │     │  style context  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Endpoint

```
POST /songs/{id}/complete
{
  "context": "current line or section",
  "position": "cursor position",
  "type": "line" | "section" | "rhyme"
}
```

---

## 2. Autopilot Mode

**"Let the agent take over"**

Full autonomous song creation. The agent drives, but stops at key decision points to get user direction—similar to how Claude Code asks for confirmation before major actions.

### How It Works

```
User:           "Write me a song about leaving home"
Agent:          "I'll create a song about leaving home. Let me start with the theme..."

[Agent works autonomously]

Agent:          "I've drafted a verse about packing bags and saying goodbye.

                 Direction needed:
                 - Should this be hopeful or melancholic?
                 - Any specific imagery you want to include?
                 - Continue with chorus next?"

User:           "Hopeful. Include imagery of open roads. Yes, continue."

[Agent continues...]
```

### Checkpoint Types

| Checkpoint | When | User Chooses |
|------------|------|--------------|
| **Theme** | Start | Mood, perspective, key imagery |
| **Structure** | After outline | Section order, song length |
| **Section** | After each section | Keep/revise, direction for next |
| **Style** | When options exist | Which of 2-3 variations |
| **Completion** | End | Final review, export options |

### Agent Behaviors

1. **Transparent reasoning**: Shows what it's thinking
2. **Incremental progress**: Completes one section at a time
3. **Undo-friendly**: Easy to backtrack to any checkpoint
4. **Style-aware**: Uses Style Library throughout

### UI Concepts

- **Progress timeline**: Visual representation of checkpoints
- **Decision cards**: Clear options at each checkpoint
- **Preview pane**: See what agent has created so far
- **"Take back control"**: User can exit autopilot anytime

### Technical Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   START     │ ──▶ │  WORK       │ ──▶ │ CHECKPOINT  │ ──┐
│   Task      │     │  Autonomously│     │  (decision) │   │
└─────────────┘     └─────────────┘     └─────────────┘   │
                           ▲                              │
                           └──────────────────────────────┘
                                    User input
```

### Endpoint

```
POST /songs/{id}/autopilot/start
{
  "prompt": "Write me a song about...",
  "preferences": { "style": "ballad", "mood": "hopeful" }
}

GET /songs/{id}/autopilot/status
→ { "state": "awaiting_input", "checkpoint": "structure", "options": [...] }

POST /songs/{id}/autopilot/continue
{
  "decision": "option_a",
  "additional_input": "Include open road imagery"
}
```

---

## 3. Ambient Mode

**"AI that writes alongside you"**

No prompts needed. Like autocorrect in Word, but instead of fixing errors, it proactively offers:
- Alternative phrasings
- Structural suggestions
- Rhyme completions
- Line variations

The user stays in flow—AI assistance appears naturally without breaking concentration.

### How It Works

```
User writes:    "The sun sets on another day"
                        ↓
AI notices:     This could rhyme, offers alternatives
                        ↓
Ambient UI:     Subtle indicator appears (not intrusive)
                • "The sun sets on another day"
                  └─ "away" "to stay" "come what may" (rhyme options)
                  └─ "As the sun dips low, painting skies" (rephrase)
                        ↓
User:           Ignores (keeps writing) OR clicks to see options
```

### What Ambient Mode Offers

| Trigger | AI Offers | UI Treatment |
|---------|-----------|--------------|
| End of line | Rhyme options | Subtle underline or margin icon |
| Weak line detected | Stronger alternatives | Wavy underline (like spell-check) |
| Repeated word | Synonyms | Highlight on hover |
| Structure opportunity | "Add a bridge here?" | Section divider suggestion |
| Melody mismatch | Syllable-adjusted versions | Prosody indicator |

### Key Principle: Non-Intrusive

- **No popups**: Suggestions are there if you want them
- **No blocking**: Never stops the user from typing
- **Dismissable**: Easy to turn off entirely or per-suggestion
- **Learn from ignores**: If user ignores a type of suggestion, offer less

### UI Concepts

- **Margin annotations**: Small icons in the gutter (click to expand)
- **Underlines**: Wavy lines under improvable phrases
- **Ghost alternatives**: On hover, show alternative phrasing
- **Settings**: Adjust sensitivity (aggressive ↔ subtle)

### Technical Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  User types     │ ──▶ │  Debounced       │ ──▶ │  Background     │
│  (real-time)    │     │  analysis        │     │  suggestions    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                         │
                                                         ▼
                                                 ┌─────────────────┐
                                                 │  Ambient UI     │
                                                 │  (non-blocking) │
                                                 └─────────────────┘
```

### Endpoint

```
# WebSocket for real-time analysis
WS /songs/{id}/ambient

→ { "type": "content_update", "content": "The sun sets on another day" }
← { "type": "suggestions", "line": 3, "suggestions": [
      { "type": "rhyme", "options": ["away", "to stay", "come what may"] },
      { "type": "rephrase", "alternative": "As the sun dips low..." }
    ]
  }
```

---

## 4. Session Mode

**"Brainstorm with AI, let it organize"**

A conversational mode where you explore ideas freely with the AI, and it organizes the results into structured sections. Think "AI songwriter session."

### How It Works

```
User:           "I want to write about leaving my hometown"
AI:             "What feelings come up when you think about leaving?"

User:           "Excitement but also guilt about leaving my parents"
AI:             "That tension is powerful. Any specific memories?"

User:           "Watching my mom wave from the porch"
AI:             "Beautiful image. Let me sketch something...

                 I've organized this into a potential structure:

                 VERSE 1 (the leaving):
                 - Porch image, mom waving
                 - Bags in the car

                 CHORUS (the tension):
                 - Excitement vs guilt
                 - Looking forward, looking back

                 Want me to draft lyrics for any section?"
```

### Key Behaviors

- **Conversational**: Ask questions, explore themes, gather raw material
- **Organizing**: AI structures unstructured brainstorming into sections
- **Non-linear**: Jump around, follow tangents, circle back
- **Collaborative**: Feel like jamming with a co-writer

### UI Concepts

- **Chat interface**: Full conversation, not just suggestions
- **Section preview**: Side panel shows emerging structure
- **Drag to editor**: Pull organized ideas into the main song
- **Session history**: Return to previous brainstorm sessions

### Endpoint

```
# WebSocket for conversational session
WS /songs/{id}/session

→ { "type": "message", "content": "I want to write about leaving home" }
← { "type": "response", "content": "What feelings come up...", "suggested_structure": null }

→ { "type": "message", "content": "Excitement but guilt" }
← { "type": "response", "content": "That tension is powerful...", "suggested_structure": {...} }

# Commit structure to song
POST /songs/{id}/session/commit
{ "sections": [...] }
```

---

## Mode Comparison

```
User Control ◀─────────────────────────────────────────────▶ AI Initiative

┌────────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
│   COMPLETION   │   │    SESSION     │   │   AUTOPILOT    │   │    AMBIENT     │
│                │   │                │   │                │   │                │
│  User asks     │   │  User explores │   │  User delegates│   │  AI offers     │
│  AI responds   │   │  AI organizes  │   │  AI drives     │   │  User accepts  │
│                │   │                │   │  (checkpoints) │   │  (or ignores)  │
└────────────────┘   └────────────────┘   └────────────────┘   └────────────────┘
     ▲                      │                     │                     │
     │                      │                     │                     ▼
     │                Conversational              │              Always running
     │                back-and-forth              │              in background
     │                      ▼                     ▼
     │               AI structures          Periodic user input
     │               the results            required to continue
     │
Explicit request required
```

---

## Implementation Priority

| Phase | Mode | Why |
|-------|------|-----|
| **Phase 3.1** | Completion | Foundation—explicit request/response |
| **Phase 3.2** | Session | Conversational brainstorming, high value |
| **Phase 3.3** | Ambient (basic) | Rhyme suggestions, simple alternatives |
| **Phase 3.4** | Autopilot | Requires robust agent infrastructure |
| **Phase 3.5** | Ambient (full) | Prosody, structure, learn from usage |

---

## User Preferences

Users should be able to:

```yaml
ai_modes:
  completion:
    enabled: true
    show_ghost_text: true
    num_alternatives: 3

  session:
    enabled: true
    auto_organize: true  # AI suggests structure as you brainstorm
    show_section_preview: true  # Side panel with emerging structure

  autopilot:
    enabled: true
    checkpoint_frequency: "normal"  # minimal | normal | detailed
    auto_continue: false  # require explicit "continue" at each checkpoint

  ambient:
    enabled: true
    sensitivity: "medium"  # subtle | medium | aggressive
    suggestion_types:
      rhymes: true
      rephrases: true
      structure: true
      prosody: false  # advanced feature
```

---

## Related Documentation

- [Style Library Vision](./vision.md) - How style context informs all modes
- [Multi-Agent Architecture](../architecture/multi_agent.md) - Agent infrastructure for Autopilot
- [Songwriter Roadmap](../roadmap/SONGWRITER_ROADMAP.md) - Implementation phases
