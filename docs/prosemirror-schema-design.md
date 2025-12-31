# ProseMirror Schema Design for Greg Song Editor

## Overview

This document defines the ProseMirror schema for the song editor, ensuring support for:
- **Versioning**: Parts have multiple versions, one is "main" (displayed)
- **Audio files**: Attached to specific versions of parts
- **Line types**: Lyrics, chords, annotations
- **Reordering**: Drag-drop parts to change order

## Terminology

| Term | Meaning |
|------|---------|
| **Part** | A segment of the song (verse, chorus, bridge, etc.) |
| **Label** | The name/title of a part ("Verse 1", "Chorus", etc.) |
| **Line** | A single line of content within a part |
| **Line Type** | Classification: lyric, chord, or annotation |

## Schema Structure

```
doc
└── part+                       # One or more parts
    ├── label                   # The part's name (e.g., "Verse 1")
    └── line*                   # Zero or more content lines
```

## Node Definitions

### Document Node
```typescript
doc: {
  content: "part+"  // Must contain one or more parts
}
```

### Part Node
The core building block. Each part has:
- A unique ID (for linking versions/audio)
- Type categorization (verse, chorus, bridge, etc.)
- Reference to which version is displayed

```typescript
part: {
  content: "label line*",
  attrs: {
    id: { default: null },           // UUID - stable identifier
    type: { default: "verse" },      // verse, chorus, bridge, pre_chorus, etc.
    mainVersionId: { default: null }, // Which version's content is displayed
  },
  draggable: true,  // Enable drag-drop reordering
}
```

### Label Node
The title/name of a part (e.g., "Verse 1", "Chorus").
- Required (every part has exactly one)
- Cannot be deleted without deleting the part
- Can be rendered inline or in gutter (UI flexibility)

```typescript
label: {
  content: "text*",
  parseDOM: [{ tag: "div.part-label" }],
  toDOM: () => ["div", { class: "part-label" }, 0],
}
```

### Line Node
Individual lines within a part. Each line has a type.

```typescript
line: {
  content: "text*",
  attrs: {
    lineType: { default: "lyric" },  // lyric, chord, annotation
  },
  parseDOM: [{ tag: "div.line" }],
  toDOM: (node) => ["div", {
    class: `line line-${node.attrs.lineType}`
  }, 0],
}
```

## Line Types

| Type | Prefix | Example | Display |
|------|--------|---------|---------|
| `lyric` | (none) | "Hello, it's me" | Normal text |
| `chord` | `> ` | "> Am G C F" | Blue, monospace |
| `annotation` | `// ` | "// soft, building" | Gray, italic |

**Input behavior:**
- Type `> ` at line start → converts to chord line
- Type `// ` at line start → converts to annotation
- Backspace at line start → resets to lyric

## How Features Work

### 1. Versioning

Each `part` node has an `id` attribute (UUID). Versions are stored separately.

**Version storage (SQL):**
```sql
part_versions (
  id UUID PRIMARY KEY,
  part_id UUID REFERENCES song_parts(id),  -- Links to part.attrs.id
  version_number INT,
  content JSONB,        -- ProseMirror node JSON for lines
  is_main BOOLEAN,
  created_at TIMESTAMP
)
```

**Switching versions:**
1. User clicks version button on part's label
2. Look up part by `id` attribute
3. Load selected version's content (lines)
4. Replace part's lines with version content
5. Update `mainVersionId` attribute

**Important:** Label is NOT part of the version. "Verse 1" stays "Verse 1" across all versions. Only the lines (content) change.

### 2. Audio Files

Audio files attach to specific versions of parts.

```sql
version_audio_files (
  id UUID PRIMARY KEY,
  version_id UUID REFERENCES part_versions(id),
  filename VARCHAR,
  storage_path VARCHAR,
  duration_seconds FLOAT,
  created_at TIMESTAMP
)
```

**UI:** Part label shows audio icon if current version has audio files.

### 3. Line Types

Each `line` node has a `lineType` attribute. No prefix parsing needed after initial input.

**Input rules:**
```typescript
// "> " at line start → chord line (prefix removed)
// "// " at line start → annotation (prefix removed)
```

**Gutter:** Shows line type icon, click to cycle through types.

### 4. Reordering (Drag-Drop)

Parts have `draggable: true`. ProseMirror handles the move.

**Key benefit:** Part `id` travels with the node. No re-linking needed. Order = position in document.

## Example Document

```json
{
  "type": "doc",
  "content": [
    {
      "type": "part",
      "attrs": {
        "id": "abc-123",
        "type": "verse",
        "mainVersionId": "ver-001"
      },
      "content": [
        {
          "type": "label",
          "content": [{ "type": "text", "text": "Verse 1" }]
        },
        {
          "type": "line",
          "attrs": { "lineType": "chord" },
          "content": [{ "type": "text", "text": "Am  G  C  F" }]
        },
        {
          "type": "line",
          "attrs": { "lineType": "lyric" },
          "content": [{ "type": "text", "text": "Hello, it's me" }]
        },
        {
          "type": "line",
          "attrs": { "lineType": "annotation" },
          "content": [{ "type": "text", "text": "soft, building" }]
        }
      ]
    },
    {
      "type": "part",
      "attrs": {
        "id": "def-456",
        "type": "chorus",
        "mainVersionId": "ver-002"
      },
      "content": [
        {
          "type": "label",
          "content": [{ "type": "text", "text": "Chorus" }]
        },
        {
          "type": "line",
          "attrs": { "lineType": "lyric" },
          "content": [{ "type": "text", "text": "I was wondering if after all these years" }]
        }
      ]
    }
  ]
}
```

## Yjs Integration

ProseMirror with Yjs uses `Y.XmlFragment` (not Y.Text):

```typescript
import * as Y from 'yjs'
import { ySyncPlugin, yCursorPlugin, yUndoPlugin } from 'y-prosemirror'

const yDoc = new Y.Doc()
const yXmlFragment = yDoc.getXmlFragment('prosemirror')

const plugins = [
  ySyncPlugin(yXmlFragment),
  yCursorPlugin(provider.awareness),
  yUndoPlugin(),
]
```

**Key difference from CodeMirror:**
- CodeMirror uses `Y.Text` (flat string)
- ProseMirror uses `Y.XmlFragment` (tree structure)
- Nodes have identity - moving a part preserves its `id`

## SQL Schema Mapping

Current SQL uses "section" terminology. We'll map in code:

| SQL Table | Maps To | Notes |
|-----------|---------|-------|
| `song_sections` | `part` node | `section.id` → `part.attrs.id` |
| `section_versions` | Version storage | Content is ProseMirror JSON |
| `lines` | `line` nodes | Within version content |

**No SQL migration needed** - we map "section" → "part" in the code layer.

## Implementation Plan

### Phase 1: Backend Yjs Schema
1. Create new Yjs schema using Y.XmlFragment
2. Conversion functions: SQL ↔ ProseMirror JSON
3. Update yjs_sync.py for new structure

### Phase 2: Frontend Editor
1. Install prosemirror packages + y-prosemirror
2. Define schema (part, label, line nodes)
3. Create basic editor component
4. Wire up Yjs sync

### Phase 3: Features
1. Line type input rules (>, //)
2. Part drag-drop reordering
3. Version switching UI
4. Audio attachment UI

### Phase 4: Migration
1. Convert existing Y.Text canvas to Y.XmlFragment
2. Test with existing songs
3. Deprecate CodeMirror component

## Design Decisions

1. **Version switching is collaborative** - All users see the same version of a part
2. **Part type from label** - Typing "Verse" auto-sets type=verse (can override)
3. **Creating parts** - Enter on empty line at end creates new part
4. **Versions in SQL** - Not Yjs. Version management is simpler without real-time sync.
