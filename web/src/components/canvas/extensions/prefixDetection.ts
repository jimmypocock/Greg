/**
 * Prefix Detection Extension for CodeMirror
 *
 * Detects when users type prefixes (# > //) followed by space
 * and automatically converts the line to the appropriate type.
 * Also handles backspace at start of line to reset to lyric type.
 *
 * IMPORTANT: Prefixes are kept in the text for persistence via Yjs.
 * The CSS hides the prefix visually, but it remains in the document.
 */

import { keymap, EditorView } from '@codemirror/view';
import { StateEffect } from '@codemirror/state';
import { LineType } from '@/types/song';
import { lineTypesField, setLineType, getLineType } from './lineTypes';

// Prefix patterns that trigger line type changes (only when followed by space)
// Note: We no longer remove the prefix - it stays in the text for persistence
const PREFIX_PATTERNS: { pattern: RegExp; type: LineType }[] = [
  { pattern: /^# /, type: LineType.SECTION_HEADER },
  { pattern: /^> /, type: LineType.CHORD },
  { pattern: /^\/\/ /, type: LineType.ANNOTATION },
];

/**
 * Parse text content and extract line types from prefixes.
 * Used for initial load to restore line types from persisted text.
 */
export function parseLineTypesFromText(text: string): Map<number, LineType> {
  const lineTypes = new Map<number, LineType>();
  const lines = text.split('\n');

  for (let i = 0; i < lines.length; i++) {
    const lineNumber = i + 1; // CodeMirror lines are 1-indexed
    const lineText = lines[i];

    let foundType = LineType.LYRIC;
    for (const { pattern, type } of PREFIX_PATTERNS) {
      if (pattern.test(lineText)) {
        foundType = type;
        break;
      }
    }
    lineTypes.set(lineNumber, foundType);
  }

  return lineTypes;
}

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
// NOTE: We no longer remove prefixes - they stay in the text for persistence
export const prefixDetector = EditorView.updateListener.of((update) => {
  if (!update.docChanged) return;

  // Check each changed line for prefix patterns
  const effects: StateEffect<{ lineNumber: number; type: LineType }>[] = [];

  update.changes.iterChangedRanges((fromA, toA, fromB, toB) => {
    // Get the line that was changed
    const line = update.state.doc.lineAt(fromB);
    const lineText = line.text;

    // Check if line starts with a prefix pattern
    let matchedType: LineType | null = null;
    for (const { pattern, type } of PREFIX_PATTERNS) {
      if (pattern.test(lineText)) {
        matchedType = type;
        break;
      }
    }

    // If no prefix found, check if we need to reset to LYRIC
    // (e.g., user deleted the prefix)
    const currentType = getLineType(update.state, line.number);

    if (matchedType !== null && currentType !== matchedType) {
      effects.push(setLineType.of({ lineNumber: line.number, type: matchedType }));
    } else if (matchedType === null && currentType !== LineType.LYRIC) {
      // Line no longer has a prefix, reset to lyric
      effects.push(setLineType.of({ lineNumber: line.number, type: LineType.LYRIC }));
    }
  });

  // Apply line type changes if any
  if (effects.length > 0) {
    // Use setTimeout to avoid dispatching during an update
    setTimeout(() => {
      try {
        update.view.dispatch({ effects });
      } catch (e) {
        // Silently ignore errors - this can happen during Yjs sync when document changes rapidly
        console.debug('[prefixDetector] Skipped stale dispatch:', e);
      }
    }, 0);
  }
});
