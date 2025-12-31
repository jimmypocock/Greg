/**
 * ProseMirror Commands for Song Editor
 *
 * Custom commands for handling Enter, Backspace, and line type conversion.
 */

import { Command, TextSelection } from 'prosemirror-state';
import { LineType, SectionType } from '@/types/song';
import { songSchema, createPart } from './schema';

/**
 * Handle Enter key in the editor.
 * - In a line: create new line
 * - In empty last line at end of part: create new part
 */
export const handleEnter: Command = (state, dispatch) => {
  const { $from } = state.selection;
  const parent = $from.parent;

  // If in a line, create a new line
  if (parent.type.name === 'line') {
    if (!dispatch) return true;

    const newLine = songSchema.node('line', { lineType: LineType.LYRIC });

    // Split at cursor or insert after
    const tr = state.tr;
    const endOfLine = $from.end();
    tr.insert(endOfLine + 1, newLine);
    tr.setSelection(TextSelection.near(tr.doc.resolve(endOfLine + 2)));
    dispatch(tr.scrollIntoView());
    return true;
  }

  // If in a label, move to first line (or create one)
  if (parent.type.name === 'label') {
    if (!dispatch) return true;

    const partNode = $from.node(-1);
    const partPos = $from.before(-1);

    // Find the first line in this part
    let linePos: number | null = null;
    partNode.forEach((child, offset) => {
      if (child.type.name === 'line' && linePos === null) {
        linePos = partPos + 1 + offset;
      }
    });

    if (linePos !== null) {
      const tr = state.tr;
      tr.setSelection(TextSelection.near(tr.doc.resolve(linePos + 1)));
      dispatch(tr.scrollIntoView());
      return true;
    }
  }

  return false;
};

/**
 * Handle Backspace at start of line.
 * - If line has a prefix, remove it and reset to lyric type
 * - If line is empty and at start of part, potentially merge with previous part
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

  // If line has a prefix (>, //), remove it and reset to lyric
  if (lineType === LineType.CHORD && lineText.startsWith('> ')) {
    if (!dispatch) return true;
    const tr = state.tr;
    tr.delete($from.pos, $from.pos + 2);
    tr.setNodeMarkup($from.before(), undefined, { lineType: LineType.LYRIC });
    dispatch(tr.scrollIntoView());
    return true;
  }

  if (lineType === LineType.ANNOTATION && lineText.startsWith('// ')) {
    if (!dispatch) return true;
    const tr = state.tr;
    tr.delete($from.pos, $from.pos + 3);
    tr.setNodeMarkup($from.before(), undefined, { lineType: LineType.LYRIC });
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
  if (text.startsWith('> ') && currentType !== LineType.CHORD) {
    return { lineType: LineType.CHORD };
  }

  if (text.startsWith('// ') && currentType !== LineType.ANNOTATION) {
    return { lineType: LineType.ANNOTATION };
  }

  // No prefix but type is set? Reset to lyric only if it was explicitly a prefix type
  if (!text.startsWith('> ') && !text.startsWith('// ') && currentType !== LineType.LYRIC) {
    return { lineType: LineType.LYRIC };
  }

  return null;
}

/**
 * Add a new part after the current one.
 */
export const addPartAfterCurrent: Command = (state, dispatch) => {
  const { $from } = state.selection;

  // Find the part we're in
  let depth = $from.depth;
  while (depth > 0 && $from.node(depth).type.name !== 'part') {
    depth--;
  }

  if (depth === 0) return false;

  const partPos = $from.after(depth);
  const newPart = createPart('New Part', SectionType.VERSE);

  if (!dispatch) return true;

  const tr = state.tr;
  tr.insert(partPos, newPart);

  // Move cursor to the label of the new part
  const labelPos = partPos + 2; // After part start and into label
  tr.setSelection(TextSelection.near(tr.doc.resolve(labelPos)));
  dispatch(tr.scrollIntoView());

  return true;
};

/**
 * Delete the current part (if there's more than one).
 */
export const deleteCurrentPart: Command = (state, dispatch) => {
  const { $from } = state.selection;

  // Find the part we're in
  let depth = $from.depth;
  while (depth > 0 && $from.node(depth).type.name !== 'part') {
    depth--;
  }

  if (depth === 0) return false;

  // Don't delete if it's the only part
  const doc = state.doc;
  if (doc.childCount <= 1) return false;

  const partStart = $from.before(depth);
  const partEnd = $from.after(depth);

  if (!dispatch) return true;

  const tr = state.tr;
  tr.delete(partStart, partEnd);
  dispatch(tr.scrollIntoView());

  return true;
};
