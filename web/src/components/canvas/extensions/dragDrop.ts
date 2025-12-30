/**
 * Drag and Drop Extension for CodeMirror
 *
 * Enables drag-and-drop reordering of sections.
 * Sections can be dragged by their drag handle and dropped on other sections.
 */

import { EditorView } from '@codemirror/view';
import { LineType } from '@/types/song';
import { getLineType } from './lineTypes';

// Custom event for section reorder (emitted by CodeMirror extension, handled by React)
export interface SectionReorderDetail {
  sourceLineNumber: number;
  targetLineNumber: number;
  insertBefore: boolean;
}

// Extension to handle drag-and-drop section reordering
export const sectionDragDrop = EditorView.domEventHandlers({
  dragover(event, view) {
    // Check if we're dragging a section
    if (!document.body.classList.contains('dragging-section')) return false;

    // Find which line we're over
    const pos = view.posAtCoords({ x: event.clientX, y: event.clientY });
    if (pos === null) return false;

    const line = view.state.doc.lineAt(pos);
    const lineType = getLineType(view.state, line.number);

    // Only allow dropping on section headers
    if (lineType === LineType.SECTION_HEADER) {
      event.preventDefault();
      event.dataTransfer!.dropEffect = 'move';

      // Add visual indicator
      const lineElement = view.domAtPos(line.from).node.parentElement;
      if (lineElement && lineElement.classList.contains('cm-line')) {
        // Remove existing drop indicators
        view.dom.querySelectorAll('.drop-target').forEach((el) => el.classList.remove('drop-target'));
        lineElement.classList.add('drop-target');
      }
      return true;
    }
    return false;
  },

  dragleave(event, view) {
    // Remove drop indicators
    view.dom.querySelectorAll('.drop-target').forEach((el) => el.classList.remove('drop-target'));
    return false;
  },

  drop(event, view) {
    // Remove drop indicators
    view.dom.querySelectorAll('.drop-target').forEach((el) => el.classList.remove('drop-target'));

    const sourceLineStr = event.dataTransfer?.getData('text/plain');
    if (!sourceLineStr) return false;

    const sourceLineNum = parseInt(sourceLineStr, 10);
    if (isNaN(sourceLineNum)) return false;

    // Find target line
    const pos = view.posAtCoords({ x: event.clientX, y: event.clientY });
    if (pos === null) return false;

    const targetLine = view.state.doc.lineAt(pos);
    const targetLineNum = targetLine.number;

    // Don't drop on self
    if (sourceLineNum === targetLineNum) return false;

    // Verify both are section headers
    const sourceType = getLineType(view.state, sourceLineNum);
    const targetType = getLineType(view.state, targetLineNum);
    if (sourceType !== LineType.SECTION_HEADER || targetType !== LineType.SECTION_HEADER) {
      return false;
    }

    // Emit custom event for React to handle via onReorderSections callback
    // This ensures the backend is updated and the song is refreshed
    const detail: SectionReorderDetail = {
      sourceLineNumber: sourceLineNum,
      targetLineNumber: targetLineNum,
      insertBefore: sourceLineNum > targetLineNum,
    };
    view.dom.dispatchEvent(new CustomEvent('section-reorder', { detail, bubbles: true }));

    event.preventDefault();
    return true;
  },
});
