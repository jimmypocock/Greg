/**
 * ProseMirror NodeViews for Song Editor
 *
 * Factory function for line node views.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { EditorView } from 'prosemirror-view';

import { LineNodeView } from './LineNodeView';

// Re-export for convenience
export { LineNodeView } from './LineNodeView';

/**
 * Create NodeView factory functions for EditorView.
 */
export function createNodeViews() {
  return {
    line: (node: ProseMirrorNode, view: EditorView, getPos: () => number | undefined) =>
      new LineNodeView(node, view, getPos),
  };
}
