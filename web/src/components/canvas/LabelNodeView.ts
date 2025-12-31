/**
 * LabelNodeView - ProseMirror NodeView for label nodes (part headers)
 *
 * Simple label display for section headers like "Verse 1", "Chorus", etc.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { EditorView, NodeView } from 'prosemirror-view';

export class LabelNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;
  private gutter: HTMLElement;

  constructor(
    node: ProseMirrorNode,
    view: EditorView,
    getPos: () => number | undefined
  ) {
    // Create wrapper
    this.dom = document.createElement('div');
    this.dom.className = 'pm-label-wrapper';

    // Create gutter element (empty for labels)
    this.gutter = document.createElement('div');
    this.gutter.className = 'pm-gutter pm-gutter-label';
    this.gutter.contentEditable = 'false';
    this.dom.appendChild(this.gutter);

    // Create content area
    this.contentDOM = document.createElement('div');
    this.contentDOM.className = 'pm-label-content';
    this.dom.appendChild(this.contentDOM);
  }

  update(node: ProseMirrorNode): boolean {
    return node.type.name === 'label';
  }

  destroy() {}
}
