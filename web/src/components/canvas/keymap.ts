/**
 * ProseMirror Keymap for Song Editor
 */

import { keymap } from 'prosemirror-keymap';
import { baseKeymap } from 'prosemirror-commands';
import { undo, redo } from 'prosemirror-history';
import { handleEnter, handleBackspaceAtLineStart, addPartAfterCurrent } from './commands';

/**
 * Create the keymap for the song editor.
 */
export function createKeymap() {
  return keymap({
    // Custom commands
    Enter: handleEnter,
    Backspace: handleBackspaceAtLineStart,

    // Add new part with Cmd/Ctrl+Shift+Enter
    'Mod-Shift-Enter': addPartAfterCurrent,

    // History (undo/redo handled by y-prosemirror in collaborative mode)
    'Mod-z': undo,
    'Mod-Shift-z': redo,
    'Mod-y': redo,
  });
}

/**
 * Get the base keymap from prosemirror-commands.
 */
export function getBaseKeymap() {
  return keymap(baseKeymap);
}
