/**
 * LabelNodeView - ProseMirror NodeView for label nodes (part headers)
 *
 * Simple label display for section headers like "Verse 1", "Chorus", etc.
 * When Shift is held, gutter shows drag icon and dragging moves the entire part.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { NodeSelection } from 'prosemirror-state';
import { EditorView, NodeView } from 'prosemirror-view';

import { DRAG_ICON } from './constants';
import { getIsShiftHeld, subscribeToShift } from './shiftTracking';

export class LabelNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;
  private gutter: HTMLElement;
  private view: EditorView;
  private getPos: () => number | undefined;
  private unsubscribeShift: () => void;

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

    // Create gutter element (empty for labels, drag icon when shift held)
    this.gutter = document.createElement('div');
    this.gutter.className = 'pm-gutter pm-gutter-label';
    this.gutter.contentEditable = 'false';
    this.dom.appendChild(this.gutter);

    // Create content area
    this.contentDOM = document.createElement('div');
    this.contentDOM.className = 'pm-label-content';
    this.dom.appendChild(this.contentDOM);

    // Set initial state
    this.updateGutter();

    // Bind event handlers
    this.handleGutterMouseDown = this.handleGutterMouseDown.bind(this);
    this.gutter.addEventListener('mousedown', this.handleGutterMouseDown);

    // Subscribe to shift key changes
    this.unsubscribeShift = subscribeToShift(() => this.updateGutter());
  }

  private updateGutter() {
    if (getIsShiftHeld()) {
      this.gutter.textContent = DRAG_ICON;
      this.gutter.classList.add('pm-gutter-drag');
      this.gutter.draggable = true;
    } else {
      this.gutter.textContent = '';
      this.gutter.classList.remove('pm-gutter-drag');
      this.gutter.draggable = false;
    }
  }

  private handleGutterMouseDown(e: MouseEvent) {
    if (!getIsShiftHeld()) return;

    // Select the parent part node so dragging moves the whole part
    const pos = this.getPos();
    if (pos !== undefined) {
      const { state } = this.view;
      // Label is inside part, so go up one level to get the part position
      const $pos = state.doc.resolve(pos);
      const partPos = $pos.before($pos.depth); // Get parent (part) position
      const selection = NodeSelection.create(state.doc, partPos);
      this.view.dispatch(state.tr.setSelection(selection));
    }
  }

  update(node: ProseMirrorNode): boolean {
    return node.type.name === 'label';
  }

  destroy() {
    this.gutter.removeEventListener('mousedown', this.handleGutterMouseDown);
    this.unsubscribeShift();
  }
}
