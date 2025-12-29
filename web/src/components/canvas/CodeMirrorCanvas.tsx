'use client';

/**
 * CodeMirror Canvas Editor
 *
 * A document-style song editor using CodeMirror for natural text editing.
 * Supports multi-line selection, copy/paste, and floating chord annotations.
 */

import { useCallback, useMemo, useRef, useEffect } from 'react';
import CodeMirror, { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { EditorView, keymap, ViewUpdate, gutter, GutterMarker, Decoration, DecorationSet, placeholder } from '@codemirror/view';
import { StateField, StateEffect, RangeSetBuilder } from '@codemirror/state';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { Song, LineType } from '@/types/song';
import { chordAnnotations, ChordAnnotation, getChords } from './chordAnnotations';
import { parseDocument, ParsedDocument, toApiFormat } from './parseDocument';

// Line type icons (match keyboard shortcuts)
const LINE_ICONS: Record<LineType, string> = {
  [LineType.SECTION_HEADER]: '#',
  [LineType.CHORD]: '>',
  [LineType.ANNOTATION]: '//',
  [LineType.LYRIC]: '',
};

// Line type cycle order (for clicking to change)
const LINE_TYPE_CYCLE: LineType[] = [
  LineType.LYRIC,
  LineType.SECTION_HEADER,
  LineType.CHORD,
  LineType.ANNOTATION,
];

// State effect to set line type
const setLineType = StateEffect.define<{ lineNumber: number; type: LineType }>();

// State field to track line types (line number -> LineType)
const lineTypesField = StateField.define<Map<number, LineType>>({
  create() {
    return new Map();
  },
  update(types, tr) {
    // Handle document changes - shift line numbers as needed
    let newTypes = types;
    if (tr.docChanged) {
      newTypes = new Map();
      const oldDoc = tr.startState.doc;
      const newDoc = tr.newDoc;

      // Track which old line number first mapped to each new line
      // This ensures when lines merge, the FIRST (surviving) line's type wins
      const firstOldLineForNew = new Map<number, number>();

      // Determine which old line each new line came from (process in order)
      for (let oldLineNum = 1; oldLineNum <= oldDoc.lines; oldLineNum++) {
        const oldLine = oldDoc.line(oldLineNum);
        const newPos = tr.changes.mapPos(oldLine.from, -1);
        if (newPos <= newDoc.length) {
          const newLineNum = newDoc.lineAt(newPos).number;
          // Only record the first old line that maps to each new line
          if (!firstOldLineForNew.has(newLineNum)) {
            firstOldLineForNew.set(newLineNum, oldLineNum);
          }
        }
      }

      // For each new line, use the type of the first old line that mapped to it
      for (const [newLineNum, oldLineNum] of firstOldLineForNew) {
        const type = types.get(oldLineNum);
        if (type) {
          newTypes.set(newLineNum, type);
        }
        // If no type, it defaults to LYRIC (no entry needed)
      }
    }

    // Apply any line type changes
    for (const effect of tr.effects) {
      if (effect.is(setLineType)) {
        newTypes = new Map(newTypes);
        newTypes.set(effect.value.lineNumber, effect.value.type);
      }
    }

    return newTypes;
  },
});

// Get line type from state
function getLineType(state: { field: (field: StateField<Map<number, LineType>>) => Map<number, LineType> }, lineNumber: number): LineType {
  const types = state.field(lineTypesField);
  return types.get(lineNumber) || LineType.LYRIC;
}

// Gutter marker that's clickable
class LineTypeMarker extends GutterMarker {
  constructor(readonly lineType: LineType) {
    super();
  }

  eq(other: LineTypeMarker) {
    return other.lineType === this.lineType;
  }

  toDOM() {
    const span = document.createElement('span');
    // Don't show icon for lyrics (default type), but keep the clickable area
    if (this.lineType === LineType.LYRIC) {
      span.textContent = ' ';
      span.className = 'line-type-icon line-type-lyric';
      span.title = 'Lyric (click to change)';
    } else {
      span.textContent = LINE_ICONS[this.lineType];
      span.className = `line-type-icon line-type-${this.lineType.toLowerCase()}`;
      span.title = `${this.lineType.replace('_', ' ')} (click to change)`;
    }
    return span;
  }
}

// Create markers for each type
const markers: Record<LineType, LineTypeMarker> = {
  [LineType.LYRIC]: new LineTypeMarker(LineType.LYRIC),
  [LineType.SECTION_HEADER]: new LineTypeMarker(LineType.SECTION_HEADER),
  [LineType.CHORD]: new LineTypeMarker(LineType.CHORD),
  [LineType.ANNOTATION]: new LineTypeMarker(LineType.ANNOTATION),
};

// Gutter that shows clickable line type icons
const lineTypeGutter = gutter({
  class: 'cm-lineType-gutter',
  markers: (view) => {
    const builder = new RangeSetBuilder<GutterMarker>();

    for (const { from, to } of view.visibleRanges) {
      for (let pos = from; pos <= to; ) {
        const line = view.state.doc.lineAt(pos);
        const lineType = getLineType(view.state, line.number);
        builder.add(line.from, line.from, markers[lineType]);
        pos = line.to + 1;
      }
    }

    return builder.finish();
  },
  domEventHandlers: {
    click: (view, line, event) => {
      const lineNumber = view.state.doc.lineAt(line.from).number;
      const currentType = getLineType(view.state, lineNumber);
      const currentIndex = LINE_TYPE_CYCLE.indexOf(currentType);
      const nextIndex = (currentIndex + 1) % LINE_TYPE_CYCLE.length;
      const nextType = LINE_TYPE_CYCLE[nextIndex];

      view.dispatch({
        effects: setLineType.of({ lineNumber, type: nextType }),
      });

      return true;
    },
  },
});

// Line decorations for styling each line type
const lineDecorations: Record<LineType, Decoration> = {
  [LineType.LYRIC]: Decoration.line({ class: 'cm-line-lyric' }),
  [LineType.SECTION_HEADER]: Decoration.line({ class: 'cm-line-section' }),
  [LineType.CHORD]: Decoration.line({ class: 'cm-line-chord' }),
  [LineType.ANNOTATION]: Decoration.line({ class: 'cm-line-annotation' }),
};

// StateField that provides line decorations based on line types
const lineTypeDecorations = StateField.define<DecorationSet>({
  create(state) {
    return buildLineDecorations(state);
  },
  update(decorations, tr) {
    if (tr.docChanged || tr.effects.some(e => e.is(setLineType))) {
      return buildLineDecorations(tr.state);
    }
    return decorations;
  },
  provide: (field) => EditorView.decorations.from(field),
});

function buildLineDecorations(state: { doc: { lines: number; line: (n: number) => { from: number } }; field: (field: StateField<Map<number, LineType>>) => Map<number, LineType> }): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  const types = state.field(lineTypesField);

  for (let i = 1; i <= state.doc.lines; i++) {
    const lineType = types.get(i) || LineType.LYRIC;
    const line = state.doc.line(i);
    builder.add(line.from, line.from, lineDecorations[lineType]);
  }

  return builder.finish();
}

// Export helper to get all line types from editor state
export function getLineTypes(state: { field: (field: StateField<Map<number, LineType>>) => Map<number, LineType>, doc: { lines: number } }): Map<number, LineType> {
  return state.field(lineTypesField);
}

// Prefix patterns that trigger line type changes (only when followed by space)
const PREFIX_PATTERNS: { pattern: RegExp; type: LineType; removeLength: number }[] = [
  { pattern: /^# /, type: LineType.SECTION_HEADER, removeLength: 2 },
  { pattern: /^> /, type: LineType.CHORD, removeLength: 2 },
  { pattern: /^\/\/ /, type: LineType.ANNOTATION, removeLength: 3 },
];

// Keymap for backspace at start of line to reset to lyric
const backspaceToLyric = keymap.of([
  {
    key: 'Backspace',
    run: (view) => {
      const { state } = view;
      const selection = state.selection.main;

      // Only handle if it's a cursor (not a selection)
      if (!selection.empty) {
        return false;
      }

      const from = selection.from;
      const line = state.doc.lineAt(from);

      // Check if cursor is at the start of a line
      if (from !== line.from) {
        return false;
      }

      // Get the line type from the state field directly
      const types = state.field(lineTypesField);
      const currentType = types.get(line.number) || LineType.LYRIC;

      // If already a lyric, let default behavior handle it
      if (currentType === LineType.LYRIC) {
        return false;
      }

      // Reset to lyric type
      view.dispatch({
        effects: setLineType.of({ lineNumber: line.number, type: LineType.LYRIC }),
      });

      return true; // We handled it, prevent default backspace
    },
  },
]);

// Extension that detects prefix typing and converts to line type
const prefixDetector = EditorView.updateListener.of((update) => {
  if (!update.docChanged) return;

  // Check each changed line for prefix patterns
  const effects: StateEffect<{ lineNumber: number; type: LineType }>[] = [];
  const changes: { from: number; to: number; insert: string }[] = [];

  update.changes.iterChangedRanges((fromA, toA, fromB, toB) => {
    // Get the line that was changed
    const line = update.state.doc.lineAt(fromB);
    const lineText = line.text;

    // Check if line starts with a prefix pattern
    for (const { pattern, type, removeLength } of PREFIX_PATTERNS) {
      if (pattern.test(lineText)) {
        const currentType = getLineType(update.state, line.number);
        if (currentType !== type) {
          effects.push(setLineType.of({ lineNumber: line.number, type }));
          // Remove the prefix
          changes.push({
            from: line.from,
            to: line.from + removeLength,
            insert: '',
          });
        }
        break;
      }
    }
  });

  // Apply changes if any
  if (effects.length > 0 || changes.length > 0) {
    // Use setTimeout to avoid dispatching during an update
    setTimeout(() => {
      update.view.dispatch({
        changes: changes.length > 0 ? changes : undefined,
        effects,
      });
    }, 0);
  }
});

interface CodeMirrorCanvasProps {
  song: Song;
  onChange?: (content: string, parsed: ParsedDocument) => void;
  onSave?: (parsed: ParsedDocument) => void;
}

/**
 * Theme extension for the editor.
 */
const baseTheme = EditorView.theme({
  '&': {
    fontSize: '14px',
    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
  },
  '.cm-content': {
    padding: '16px 0',
    minHeight: '200px',
  },
  '.cm-line': {
    padding: '2px 8px',
  },
  '.cm-gutters': {
    backgroundColor: 'transparent',
    border: 'none',
    paddingRight: '4px',
  },
  '.cm-lineType-gutter': {
    width: '24px',
    textAlign: 'center',
  },
  '.cm-lineType-gutter .cm-gutterElement': {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    padding: '2px 0',
  },
  '&.cm-focused .cm-cursor': {
    borderLeftColor: '#3b82f6',
  },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground': {
    backgroundColor: 'rgba(59, 130, 246, 0.2)',
  },
  '.cm-activeLine': {
    backgroundColor: 'rgba(59, 130, 246, 0.05)',
  },
});

/**
 * Convert song structure to plain text (no prefixes).
 * Returns text, chord annotations, and initial line types.
 */
function songToTextAndChords(song: Song): {
  text: string;
  chords: ChordAnnotation[];
  lineTypes: Map<number, LineType>;
} {
  const lines: string[] = [];
  const chords: ChordAnnotation[] = [];
  const lineTypes = new Map<number, LineType>();
  let lineNumber = 1; // CodeMirror lines are 1-indexed

  for (const section of song.sections) {
    // Section header (just the name, no prefix)
    const typeName = section.type.charAt(0).toUpperCase() + section.type.slice(1).replace('_', ' ');
    const headerText = section.number && section.number > 0
      ? `${typeName} ${section.number}`
      : typeName;
    lines.push(headerText);
    lineTypes.set(lineNumber, LineType.SECTION_HEADER);
    lineNumber++;

    // Section lines
    for (const line of section.lines) {
      lines.push(line.text);
      lineTypes.set(lineNumber, line.line_type || LineType.LYRIC);

      // Extract chord placements from this line
      if (line.chords && line.chords.length > 0) {
        for (const placement of line.chords) {
          chords.push({
            line: lineNumber - 1, // 0-indexed for chord annotations
            position: placement.position,
            chord: placement.chord,
          });
        }
      }

      lineNumber++;
    }

    // Empty line between sections
    lines.push('');
    lineTypes.set(lineNumber, LineType.LYRIC);
    lineNumber++;
  }

  // If no sections, just return empty or raw input
  if (lines.length === 0) {
    return { text: song.raw_input || '', chords: [], lineTypes: new Map() };
  }

  return { text: lines.join('\n').trim(), chords, lineTypes };
}

export function CodeMirrorCanvas({
  song,
  onChange,
  onSave,
}: CodeMirrorCanvasProps) {
  const editorRef = useRef<ReactCodeMirrorRef>(null);

  // Initial content, chords, and line types from song
  const { text: initialContent, chords: initialChords, lineTypes: initialLineTypes } = useMemo(
    () => songToTextAndChords(song),
    [song]
  );

  // Extensions (memoize to avoid re-creating on every render)
  const extensions = useMemo(() => [
    history(),
    backspaceToLyric, // Must come before default keymap
    keymap.of([...defaultKeymap, ...historyKeymap]),
    lineTypesField.init(() => initialLineTypes),
    lineTypeDecorations,
    lineTypeGutter,
    prefixDetector,
    baseTheme,
    EditorView.lineWrapping,
    chordAnnotations(initialChords),
    placeholder('Write your next hit...'),
    EditorView.contentAttributes.of({ 'aria-label': 'Song editor' }),
  ], [initialChords, initialLineTypes]);

  const handleChange = useCallback((value: string, viewUpdate: ViewUpdate) => {
    // Parse the document with current chord annotations and line types
    const chords = getChords(viewUpdate.state);
    const lineTypes = viewUpdate.state.field(lineTypesField);
    const parsed = parseDocument(value, chords, lineTypes);
    onChange?.(value, parsed);
  }, [onChange]);

  // Save on Cmd/Ctrl+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        // Get current editor state for chords and line types
        const view = editorRef.current?.view;
        if (view) {
          const text = view.state.doc.toString();
          const chords = getChords(view.state);
          const lineTypes = view.state.field(lineTypesField);
          const parsed = parseDocument(text, chords, lineTypes);
          onSave?.(parsed);
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onSave]);

  return (
    <div className="codemirror-canvas w-full max-w-3xl mx-auto">
      {/* Header hints */}
      <div className="mb-2 text-xs text-gray-400 dark:text-gray-500 flex gap-4 px-2">
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded font-semibold">#</code> section
        </span>
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded font-semibold">&gt;</code> chord
        </span>
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded font-semibold">//</code> note
        </span>
      </div>

      {/* Editor */}
      <div>
        <CodeMirror
          ref={editorRef}
          value={initialContent}
          extensions={extensions}
          onChange={handleChange}
          placeholder="Start writing your song...

# Verse 1
Write your first verse lyrics here

# Chorus
Your chorus goes here

> Am G C F
Add chord progressions with >"
          basicSetup={{
            lineNumbers: false,
            foldGutter: false,
            dropCursor: true,
            allowMultipleSelections: true,
            indentOnInput: false,
            bracketMatching: false,
            closeBrackets: false,
            autocompletion: false,
            highlightActiveLine: true,
            highlightSelectionMatches: false,
            searchKeymap: true,
          }}
          className="song-editor"
        />
      </div>

      {/* Footer hints */}
      <div className="mt-2 text-xs text-gray-400 dark:text-gray-500 px-2">
        Type prefix to set type · Click gutter to change type · Cmd+S to save
      </div>

      {/* CSS for line type styling */}
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;600;700&display=swap');

        .song-editor .cm-editor {
          background: transparent;
        }
        .song-editor .cm-scroller {
          font-family: "Roboto Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
        }
        .song-editor .cm-placeholder {
          color: #9ca3af;
          font-style: italic;
        }

        /* Line type gutter icons */
        .line-type-icon {
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          user-select: none;
          opacity: 0.6;
          transition: opacity 0.15s;
          line-height: 1;
        }
        .cm-gutterElement:hover .line-type-icon {
          opacity: 1;
        }
        .cm-lineType-gutter {
          background-color: #f9fafb;
          padding: 0 4px;
        }
        .dark .cm-lineType-gutter {
          background-color: #1f2937;
        }
        .cm-lineType-gutter .cm-gutterElement {
          cursor: pointer;
        }

        /* Gutter icon colors */
        .line-type-section { color: #333333; font-weight: bold; }
        .line-type-chord { color: #2563eb; }
        .line-type-annotation { color: #6b7280; }
        .line-type-lyric { color: #9ca3af; }
        .dark .line-type-section { color: #e5e5e5; }

        /* === LINE CONTENT STYLES === */

        /* Lyric lines - default, clean look */
        .cm-line-lyric {
          color: #333333;
        }
        .dark .cm-line-lyric {
          color: #e5e5e5;
        }

        /* Section headers - bold, dark, larger */
        .cm-line-section {
          color: #333333;
          font-weight: 700;
          font-size: 1.1em;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .dark .cm-line-section {
          color: #e5e5e5;
        }

        /* Chord lines - blue, monospace */
        .cm-line-chord {
          color: #2563eb;
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
          font-size: 0.9em;
          letter-spacing: 0.1em;
        }
        .dark .cm-line-chord {
          color: #60a5fa;
        }

        /* Annotation lines - italic, muted */
        .cm-line-annotation {
          color: #6b7280;
          font-style: italic;
          opacity: 0.8;
        }
        .dark .cm-line-annotation {
          color: #9ca3af;
        }
      `}</style>
    </div>
  );
}
