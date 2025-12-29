'use client';

/**
 * CodeMirror Canvas Editor
 *
 * A document-style song editor using CodeMirror for natural text editing.
 * Supports multi-line selection, copy/paste, and floating chord annotations.
 */

import { useCallback, useMemo, useRef, useEffect } from 'react';
import CodeMirror, { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { EditorView, keymap, ViewUpdate, gutter, GutterMarker } from '@codemirror/view';
import { StateField, StateEffect, RangeSetBuilder } from '@codemirror/state';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import { Song, LineType } from '@/types/song';
import { chordAnnotations, ChordAnnotation, getChords } from './chordAnnotations';
import { parseDocument, ParsedDocument, toApiFormat } from './parseDocument';

// Line type icons
const LINE_ICONS: Record<LineType, string> = {
  [LineType.SECTION_HEADER]: '§',
  [LineType.CHORD]: '♪',
  [LineType.ANNOTATION]: '✎',
  [LineType.LYRIC]: '¶',
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

      // Map old line numbers to new line numbers
      for (const [oldLineNum, type] of types) {
        if (oldLineNum <= oldDoc.lines) {
          const oldLine = oldDoc.line(oldLineNum);
          // Find where this line ended up
          const newPos = tr.changes.mapPos(oldLine.from, 1);
          if (newPos < newDoc.length) {
            const newLineNum = newDoc.lineAt(newPos).number;
            newTypes.set(newLineNum, type);
          }
        }
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
      const { from } = state.selection.main;

      // Check if cursor is at the start of a line
      const line = state.doc.lineAt(from);
      if (from !== line.from) {
        // Not at start of line, let default behavior handle it
        return false;
      }

      // Check if this line has a non-lyric type
      const currentType = getLineType(state, line.number);
      if (currentType === LineType.LYRIC) {
        // Already a lyric, let default behavior handle it (join with previous line)
        return false;
      }

      // Reset to lyric type
      view.dispatch({
        effects: setLineType.of({ lineNumber: line.number, type: LineType.LYRIC }),
      });

      return true; // We handled it
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
    lineTypeGutter,
    prefixDetector,
    baseTheme,
    EditorView.lineWrapping,
    chordAnnotations(initialChords),
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
      <div className="mb-2 text-xs text-gray-400 dark:text-gray-500 flex gap-3 px-2">
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">#</code> section
        </span>
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">&gt;</code> chord
        </span>
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">//</code> note
        </span>
        <span className="text-gray-300 dark:text-gray-600">|</span>
        <span>or click gutter icon</span>
      </div>

      {/* Editor */}
      <div className="bg-white dark:bg-gray-900 rounded-lg">
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
        Type prefix to set type · Backspace at start resets to lyric · Cmd+S to save
      </div>

      {/* CSS variables for syntax highlighting */}
      <style jsx global>{`
        .song-editor .cm-editor {
          background: transparent;
        }
        .song-editor .cm-scroller {
          font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
        }
        :root {
          --song-header-color: #1f2937;
          --song-chord-color: #2563eb;
          --song-annotation-color: #6b7280;
        }
        .dark {
          --song-header-color: #f3f4f6;
          --song-chord-color: #60a5fa;
          --song-annotation-color: #9ca3af;
        }
        /* Line type gutter icons */
        .line-type-icon {
          font-size: 12px;
          cursor: pointer;
          user-select: none;
          opacity: 0.5;
          transition: opacity 0.15s;
        }
        .cm-gutterElement:hover .line-type-icon {
          opacity: 1;
        }
        .cm-lineType-gutter .cm-gutterElement {
          cursor: pointer;
        }
        .line-type-section {
          color: var(--song-header-color, #1f2937);
          font-weight: bold;
        }
        .line-type-chord {
          color: var(--song-chord-color, #2563eb);
        }
        .line-type-annotation {
          color: var(--song-annotation-color, #6b7280);
        }
        .line-type-lyric {
          color: #9ca3af;
        }
      `}</style>
    </div>
  );
}
