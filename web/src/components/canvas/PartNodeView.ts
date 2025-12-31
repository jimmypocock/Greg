/**
 * PartNodeView - ProseMirror NodeView for part nodes (sections)
 *
 * This is a simple wrapper for parts/sections.
 * Drag is initiated via LabelNodeView's drag handle using ProseMirror's native drag.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { EditorView, NodeView } from 'prosemirror-view';

export class PartNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;

  constructor(
    node: ProseMirrorNode,
    view: EditorView,
    getPos: () => number | undefined
  ) {
    this.dom = document.createElement('div');
    this.dom.className = 'pm-part';
    this.dom.setAttribute('data-part-id', node.attrs.id || '');

    this.contentDOM = this.dom;
  }

  update(node: ProseMirrorNode): boolean {
    if (node.type.name !== 'part') return false;
    this.dom.setAttribute('data-part-id', node.attrs.id || '');
    return true;
  }

  destroy() {}
}
