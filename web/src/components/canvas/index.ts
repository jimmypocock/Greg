/**
 * Canvas - Song Editor Components
 *
 * Exports:
 * - CanvasPanel: Main panel component (self-contained with Yjs)
 * - ProseMirrorEditor: Core editor component
 * - songSchema: ProseMirror schema definition
 * - Utility functions for document conversion
 */

export { CanvasPanel } from './CanvasPanel';
export { Canvas } from './Canvas';
export { songSchema, createEmptyDoc, createPart } from './schema';
export {
  docToParts,
  docToCanvasSections,
  docToText,
  getPartIds,
  findPartById,
  type PartData,
} from './utils';
