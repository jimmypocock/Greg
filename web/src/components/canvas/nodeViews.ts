/**
 * ProseMirror NodeViews for Song Editor
 *
 * Custom node rendering with integrated gutters.
 * Each line/label renders its own gutter cell, guaranteeing alignment.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { EditorView, NodeView } from 'prosemirror-view';
import { NodeSelection } from 'prosemirror-state';
import { LineType } from '@/types/song';

// Line type cycle order (for gutter click cycling)
const LINE_TYPE_CYCLE: LineType[] = [
  LineType.LYRIC,
  LineType.SECTION_HEADER,
  LineType.CHORD,
  LineType.ANNOTATION,
];

/**
 * NodeView for line nodes.
 * Uses CSS ::before for gutter (no DOM element = no caret navigation issues)
 */
export class LineNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;
  private node: ProseMirrorNode;
  private view: EditorView;
  private getPos: () => number | undefined;

  constructor(
    node: ProseMirrorNode,
    view: EditorView,
    getPos: () => number | undefined
  ) {
    this.node = node;
    this.view = view;
    this.getPos = getPos;

    // Create wrapper - gutter is rendered via CSS ::before
    this.dom = document.createElement('div');
    this.dom.className = 'pm-line-wrapper';
    this.dom.addEventListener('click', this.handleClick);

    // Create content area
    this.contentDOM = document.createElement('div');
    this.contentDOM.className = 'pm-line-content';
    this.dom.appendChild(this.contentDOM);

    // Set line type (must be after contentDOM is created)
    this.updateLineType();
  }

  private updateLineType() {
    const lineType = (this.node.attrs.lineType as LineType) || LineType.LYRIC;
    this.dom.setAttribute('data-line-type', lineType);
    this.contentDOM.className = `pm-line-content pm-line-${lineType.toLowerCase()}`;
  }

  private handleClick = (e: MouseEvent) => {
    // Check if click is in the gutter area (left 32px)
    const rect = this.dom.getBoundingClientRect();
    const clickX = e.clientX - rect.left;

    if (clickX > 32) return; // Click was in content area, not gutter

    e.preventDefault();
    e.stopPropagation();

    const pos = this.getPos();
    if (pos === undefined) return;

    const currentType = this.node.attrs.lineType as LineType;
    const currentIndex = LINE_TYPE_CYCLE.indexOf(currentType);
    const nextType = LINE_TYPE_CYCLE[(currentIndex + 1) % LINE_TYPE_CYCLE.length];

    // Update line type and prefix
    const text = this.node.textContent;
    let newText = text;

    // Remove old prefix
    if (text.startsWith('# ')) newText = text.slice(2);
    else if (text.startsWith('> ')) newText = text.slice(2);
    else if (text.startsWith('// ')) newText = text.slice(3);

    // Add new prefix
    if (nextType === LineType.SECTION_HEADER) newText = '# ' + newText;
    else if (nextType === LineType.CHORD) newText = '> ' + newText;
    else if (nextType === LineType.ANNOTATION) newText = '// ' + newText;

    const tr = this.view.state.tr;
    tr.setNodeMarkup(pos, undefined, { lineType: nextType });

    // Replace text content if changed
    if (newText !== text) {
      const start = pos + 1;
      const end = pos + this.node.nodeSize - 1;
      if (newText) {
        tr.replaceWith(start, end, this.view.state.schema.text(newText));
      } else {
        tr.delete(start, end);
      }
    }

    this.view.dispatch(tr);
    this.view.focus();
  };

  update(node: ProseMirrorNode): boolean {
    if (node.type !== this.node.type) return false;
    this.node = node;
    this.updateLineType();
    return true;
  }

  destroy() {
    this.dom.removeEventListener('click', this.handleClick);
  }
}

/**
 * NodeView for label nodes (part headers).
 * Includes a drag handle that triggers ProseMirror's native drag behavior.
 */
export class LabelNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;
  private dragHandle: HTMLElement;
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

    // Create drag handle - draggable so it can initiate native drag
    this.dragHandle = document.createElement('div');
    this.dragHandle.className = 'pm-drag-handle';
    this.dragHandle.contentEditable = 'false';
    this.dragHandle.draggable = true;
    this.dragHandle.innerHTML = '⋮⋮'; // Grip icon
    this.dom.appendChild(this.dragHandle);

    // Create content area
    this.contentDOM = document.createElement('div');
    this.contentDOM.className = 'pm-label-content';
    this.dom.appendChild(this.contentDOM);

    // Bind event handlers
    this.handleDragStart = this.handleDragStart.bind(this);
    this.dragHandle.addEventListener('dragstart', this.handleDragStart);
  }

  private getPartPos(): number | null {
    const pos = this.getPos();
    if (pos === undefined) return null;

    // Walk up to find the parent part
    const $pos = this.view.state.doc.resolve(pos);
    for (let d = $pos.depth; d >= 1; d--) {
      const node = $pos.node(d);
      if (node.type.name === 'part') {
        return $pos.before(d);
      }
    }
    return null;
  }

  private handleDragStart(e: DragEvent) {
    const partPos = this.getPartPos();
    if (partPos === null) {
      e.preventDefault();
      return;
    }

    // Select the part node - this tells ProseMirror what we're dragging
    const tr = this.view.state.tr.setSelection(
      NodeSelection.create(this.view.state.doc, partPos)
    );
    this.view.dispatch(tr);

    // Let ProseMirror's native drag handle the rest
    // The dropCursor plugin will show where it'll land
  }

  update(node: ProseMirrorNode): boolean {
    return node.type.name === 'label';
  }

  destroy() {
    this.dragHandle.removeEventListener('dragstart', this.handleDragStart);
  }
}

/**
 * NodeView for part nodes (sections).
 * Drag is initiated via LabelNodeView's drag handle using ProseMirror's native drag.
 */
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
