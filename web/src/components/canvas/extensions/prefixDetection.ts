/**
 * Prefix Detection Extension for CodeMirror
 *
 * Detects when users type prefixes (# > //) followed by space
 * and automatically converts the line to the appropriate type.
 * Also handles backspace at start of line to reset to lyric type.
 */

import { keymap, EditorView } from '@codemirror/view';
import { StateEffect } from '@codemirror/state';
import { LineType } from '@/types/song';
import { lineTypesField, setLineType, getLineType } from './lineTypes';

// Prefix patterns that trigger line type changes (only when followed by space)
const PREFIX_PATTERNS: { pattern: RegExp; type: LineType; removeLength: number }[] = [
  { pattern: /^# /, type: LineType.SECTION_HEADER, removeLength: 2 },
  { pattern: /^> /, type: LineType.CHORD, removeLength: 2 },
  { pattern: /^\/\/ /, type: LineType.ANNOTATION, removeLength: 3 },
];

// Keymap for backspace at start of line to reset to lyric
export const backspaceToLyric = keymap.of([
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
export const prefixDetector = EditorView.updateListener.of((update) => {
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
