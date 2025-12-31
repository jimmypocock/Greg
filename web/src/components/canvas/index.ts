/**
 * Canvas - Song Editor Components
 *
 * Exports:
 * - CanvasPanel: Main panel component (self-contained with Yjs)
 * - Canvas: Core editor component
 * - songSchema: ProseMirror schema definition
 * - Utility functions for document conversion
 */

export { CanvasPanel } from './CanvasPanel';
export { Canvas } from './Canvas';
export { songSchema, createEmptyDoc, createLine } from './schema';
export {
  docToLines,
  docToCanvasLines,
  docToText,
  getLineIds,
  findLineById,
  type LineData,
} from './utils';
