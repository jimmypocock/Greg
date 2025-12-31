/**
 * LabelNodeView - ProseMirror NodeView for label nodes (part headers)
 *
 * Simple label display for section headers like "Verse 1", "Chorus", etc.
 * Drag from gutter to reorder entire parts/sections.
 */

import { Node as ProseMirrorNode, DOMSerializer } from 'prosemirror-model';
import { NodeSelection } from 'prosemirror-state';
import { EditorView, NodeView } from 'prosemirror-view';

import { DRAG_ICON } from './constants';

export class LabelNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;
  private gutter: HTMLElement;
  private view: EditorView;
  private getPos: () => number | undefined;

  constructor(
    node: ProseMirrorNode,
    view: EditorView,
    getPos: () => number | undefined
  ) {
    this.view = view;
    this.getPos = getPos;

    // Create wrapper
    this.dom = document.createElement('div');
    this.dom.className = 'pm-label-wrapper';

    // Create gutter element (drag handle for the entire part)
    this.gutter = document.createElement('div');
    this.gutter.className = 'pm-gutter pm-gutter-label';
    this.gutter.contentEditable = 'false';
    this.gutter.draggable = true;
    this.gutter.textContent = DRAG_ICON;
    this.dom.appendChild(this.gutter);

    // Create content area
    this.contentDOM = document.createElement('div');
    this.contentDOM.className = 'pm-label-content';
    this.dom.appendChild(this.contentDOM);

    // Bind event handlers
    this.handleDragStart = this.handleDragStart.bind(this);
    this.gutter.addEventListener('dragstart', this.handleDragStart);
  }

  private handleDragStart(e: DragEvent) {
    const pos = this.getPos();
    if (pos === undefined || !e.dataTransfer) return;

    const { state } = this.view;
    // Label is inside part, so go up one level to get the part position
    const $pos = state.doc.resolve(pos);
    const partPos = $pos.before($pos.depth);
    const partNode = state.doc.nodeAt(partPos);

    if (!partNode) return;

    // Select the part node
    const selection = NodeSelection.create(state.doc, partPos);
    this.view.dispatch(state.tr.setSelection(selection));

    // Serialize the part to HTML for the drag data
    const slice = selection.content();
    const serializer = DOMSerializer.fromSchema(state.schema);
    const fragment = serializer.serializeFragment(slice.content);
    const div = document.createElement('div');
    div.appendChild(fragment);

    e.dataTransfer.setData('text/html', div.innerHTML);
    e.dataTransfer.setData('text/plain', partNode.textContent);
    e.dataTransfer.effectAllowed = 'move';
  }

  update(node: ProseMirrorNode): boolean {
    return node.type.name === 'label';
  }

  destroy() {
    this.gutter.removeEventListener('dragstart', this.handleDragStart);
  }
}
