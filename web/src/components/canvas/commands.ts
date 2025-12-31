/**
 * ProseMirror Commands for Song Editor
 *
 * Custom commands for handling Enter, Backspace, and line type conversion.
 */

import { Command, TextSelection } from 'prosemirror-state';
import { LineType } from '@/types/song';
import { songSchema } from './schema';

/**
 * Handle Enter key in the editor.
 * Creates a new line after the current one.
 */
export const handleEnter: Command = (state, dispatch) => {
  const { $from } = state.selection;
  const parent = $from.parent;

  // If in a line, create a new line
  if (parent.type.name === 'line') {
    if (!dispatch) return true;

    const newLine = songSchema.node('line', {
      id: crypto.randomUUID(),
      lineType: LineType.LYRIC,
    });

    // Split at cursor or insert after
    const tr = state.tr;
    const endOfLine = $from.end();
    tr.insert(endOfLine + 1, newLine);
    tr.setSelection(TextSelection.near(tr.doc.resolve(endOfLine + 2)));
    dispatch(tr.scrollIntoView());
    return true;
  }

  return false;
};

/**
 * Handle Backspace at start of line.
 * If line has a prefix, remove it and reset to lyric type.
 */
export const handleBackspaceAtLineStart: Command = (state, dispatch) => {
  const { $from, empty } = state.selection;

  if (!empty) return false;

  const parent = $from.parent;
  if (parent.type.name !== 'line') return false;

  // Check if cursor is at start of line content
  const lineStart = $from.start();
  if ($from.pos !== lineStart) return false;

  const lineText = parent.textContent;
  const lineType = parent.attrs.lineType;

  // If line has a prefix (>, //, #), remove it and reset to lyric
  if (lineType === LineType.CHORD && lineText.startsWith('> ')) {
    if (!dispatch) return true;
    const tr = state.tr;
    tr.delete($from.pos, $from.pos + 2);
    tr.setNodeMarkup($from.before(), undefined, { ...parent.attrs, lineType: LineType.LYRIC });
    dispatch(tr.scrollIntoView());
    return true;
  }

  if (lineType === LineType.ANNOTATION && lineText.startsWith('// ')) {
    if (!dispatch) return true;
    const tr = state.tr;
    tr.delete($from.pos, $from.pos + 3);
    tr.setNodeMarkup($from.before(), undefined, { ...parent.attrs, lineType: LineType.LYRIC });
    dispatch(tr.scrollIntoView());
    return true;
  }

  if (lineType === LineType.SECTION_HEADER && lineText.startsWith('# ')) {
    if (!dispatch) return true;
    const tr = state.tr;
    tr.delete($from.pos, $from.pos + 2);
    tr.setNodeMarkup($from.before(), undefined, { ...parent.attrs, lineType: LineType.LYRIC });
    dispatch(tr.scrollIntoView());
    return true;
  }

  return false;
};

/**
 * Detect prefix typing and convert line type.
 * Called after text input.
 */
export function checkPrefixConversion(state: ReturnType<typeof import('prosemirror-state').EditorState.create>) {
  const { $from } = state.selection;
  const parent = $from.parent;

  if (parent.type.name !== 'line') return null;

  const text = parent.textContent;
  const currentType = parent.attrs.lineType;

  // Check for prefix patterns
  if (text.startsWith('# ') && currentType !== LineType.SECTION_HEADER) {
    return { lineType: LineType.SECTION_HEADER };
  }

  if (text.startsWith('> ') && currentType !== LineType.CHORD) {
    return { lineType: LineType.CHORD };
  }

  if (text.startsWith('// ') && currentType !== LineType.ANNOTATION) {
    return { lineType: LineType.ANNOTATION };
  }

  // No prefix but type is set? Reset to lyric
  if (
    !text.startsWith('# ') &&
    !text.startsWith('> ') &&
    !text.startsWith('// ') &&
    currentType !== LineType.LYRIC
  ) {
    return { lineType: LineType.LYRIC };
  }

  return null;
}
