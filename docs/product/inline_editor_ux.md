# Inline Editor UX

> **Google Docs-style editing: everything in one place.**

## Current State

```
Left pane: Edit lyrics (SectionNavigator with inline line editing)
Center pane: Preview + edit chords only (ChordEditor popover)
```

**The Problem:** Bouncing between panes to build a song. Edit lyrics left, add chords center. Functional but not fluid.

---

## Target UX

Center pane becomes THE editor. Everything inline:

- Click on a lyric line → edit in place
- Click above lyrics → add/edit chord
- Press Enter at end of line → add new line
- Add new sections with "+" or keyboard shortcut
- Left pane becomes navigation/overview only

```
Left Pane (Slim)              Center Pane (Main Editor)
┌─────────────────┐          ┌────────────────────────────────┐
│ Song Metadata   │          │ [VERSE 1]                      │
│ Key: G | 120bpm │          │     G        C         D       │
├─────────────────┤          │ This is the first line_        │ ← click to edit
│ Structure       │          │     Em       C                 │
│ ○ Verse 1      │ ←click   │ Second line of the verse       │
│ ○ Chorus       │  scrolls │                                │
│ ○ Verse 2      │  center  │ [+ Add Line]                   │
│ ○ Bridge       │          │                                │
│ [+ Section]     │          │ [CHORUS]                       │
├─────────────────┤          │     G        D         C       │
│ Audio Files     │          │ This is the chorus...          │
└─────────────────┘          └────────────────────────────────┘
```

---

## Key Changes

| Component | Current | Target |
|-----------|---------|--------|
| `EditableLineDisplay` | Chord editing only | Primary editor (lyrics + chords) |
| `SectionNavigator` | Line editing | Navigation only (click to scroll, drag to reorder) |
| Lyric editing | Left pane | Inline in center (click → input → blur/Enter saves) |
| Add line | Left pane | Inline (Enter at end, or "+ Add Line" button) |
| Section management | Separate | Inline headers (editable type, "+" between sections) |

---

## Interaction Patterns

### Editing a Line

```
1. User clicks lyric text
2. Line becomes editable input (cursor at click position)
3. User types
4. Blur or Enter saves
5. Escape cancels
```

### Adding Chords

```
1. User clicks above lyric (in chord zone)
2. ChordEditor popover opens
3. User types chord (autocomplete)
4. Click elsewhere closes
```

### Adding a Line

```
Option A: Press Enter at end of current line
Option B: Click "+ Add Line" button after last line
Option C: Keyboard shortcut (Cmd+Enter anywhere in section)
```

### Reordering

```
Left pane: Drag sections to reorder
Center pane: Drag lines within section (optional)
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Save line, move to next (or create new) |
| `Escape` | Cancel editing |
| `Tab` | Move to next line |
| `Shift+Tab` | Move to previous line |
| `Cmd+Enter` | Add new line after current |
| `Cmd+Shift+Enter` | Add new section after current |
| `Cmd+/` | Toggle chord visibility |
| `Cmd+D` | Duplicate current line |

---

## Component Architecture

```
SongEditor
├── LeftPane
│   ├── SongMetadata (key, tempo, time sig)
│   ├── SectionNavigator (click to scroll, drag to reorder)
│   └── AudioFiles (collapsed panel)
│
├── CenterPane (MainEditor)
│   └── SectionList
│       └── Section
│           ├── SectionHeader (editable type, drag handle)
│           ├── EditableLines
│           │   └── EditableLine
│           │       ├── ChordZone (click to add/edit)
│           │       └── LyricZone (click to edit inline)
│           └── AddLineButton
│
└── RightPane (optional)
    ├── AI Chat
    └── Toolbox
```

---

## Implementation Steps

1. **Make center lyrics editable inline**
   - Add click handler to lyric text
   - Render `<input>` when editing
   - Handle blur/Enter/Escape

2. **Add line inline**
   - Enter at end of line creates new line
   - Add "+ Add Line" button after last line in section

3. **Convert left pane to navigation only**
   - Remove line editing from SectionNavigator
   - Keep section reordering
   - Click section → scroll center pane

4. **Add section inline**
   - "+" button between sections
   - Section type dropdown in header

5. **Keyboard shortcuts**
   - Implement navigation (Tab, Shift+Tab)
   - Implement actions (Cmd+Enter, etc.)

---

## Related Documentation

- [AI Interaction Modes](./ai_interaction_modes.md) - How AI assists during editing
- [Songwriter Roadmap](../roadmap/SONGWRITER_ROADMAP.md) - Feature phases
