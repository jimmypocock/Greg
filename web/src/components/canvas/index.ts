/**
 * Canvas Editor Components
 *
 * A flat, document-style song editor.
 */

export { CanvasEditor } from './CanvasEditor';
export { CanvasLine } from './CanvasLine';
export { CanvasLineGutter } from './CanvasLineGutter';
export { useCanvasEditor } from './useCanvasEditor';
export { CodeMirrorCanvas } from './CodeMirrorCanvas';
export { parseDocument, toApiFormat } from './parseDocument';
export type { ParsedDocument, ParsedSection, ParsedLine } from './parseDocument';
export type { ChordAnnotation } from './chordAnnotations';
export * from './types';
