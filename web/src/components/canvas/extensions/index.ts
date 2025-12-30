/**
 * CodeMirror Extensions for Canvas Editor
 *
 * Re-exports all custom extensions for easy importing.
 */

// Line types
export {
  LINE_ICONS,
  LINE_TYPE_CYCLE,
  setLineType,
  lineTypesField,
  getLineType,
  getLineTypes,
  lineTypeGutter,
  lineTypeDecorations,
} from './lineTypes';

// Section controls
export { sectionControlsDecorations, getSectionRange } from './sectionControls';

// Drag and drop
export { sectionDragDrop } from './dragDrop';
export type { SectionReorderDetail } from './dragDrop';

// Prefix detection
export { backspaceToLyric, prefixDetector } from './prefixDetection';
