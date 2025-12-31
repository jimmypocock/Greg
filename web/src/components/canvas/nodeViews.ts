/**
 * ProseMirror NodeViews for Song Editor
 *
 * Factory function and re-exports for all node views.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { EditorView } from 'prosemirror-view';

import { LineNodeView } from './LineNodeView';
import { LabelNodeView } from './LabelNodeView';
import { PartNodeView } from './PartNodeView';

// Re-export for convenience
export { LineNodeView } from './LineNodeView';
export { LabelNodeView } from './LabelNodeView';
export { PartNodeView } from './PartNodeView';

/**
 * Create NodeView factory functions for EditorView.
 */
export function createNodeViews() {
  return {
    line: (node: ProseMirrorNode, view: EditorView, getPos: () => number | undefined) =>
      new LineNodeView(node, view, getPos),
    label: (node: ProseMirrorNode, view: EditorView, getPos: () => number | undefined) =>
      new LabelNodeView(node, view, getPos),
    part: (node: ProseMirrorNode, view: EditorView, getPos: () => number | undefined) =>
      new PartNodeView(node, view, getPos),
  };
}
