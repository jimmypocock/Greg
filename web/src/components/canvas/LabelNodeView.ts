/**
 * LabelNodeView - ProseMirror NodeView for label nodes (part headers)
 *
 * Simple label display for section headers like "Verse 1", "Chorus", etc.
 * When Shift is held, gutter shows drag icon.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { EditorView, NodeView } from 'prosemirror-view';

import { DRAG_ICON } from './constants';
import { getIsShiftHeld, subscribeToShift } from './shiftTracking';

export class LabelNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;
  private gutter: HTMLElement;
  private unsubscribeShift: () => void;

  constructor(
    node: ProseMirrorNode,
    view: EditorView,
    getPos: () => number | undefined
  ) {
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

    // Subscribe to shift key changes
    this.unsubscribeShift = subscribeToShift(() => this.updateGutter());
  }

  private updateGutter() {
    if (getIsShiftHeld()) {
      this.gutter.textContent = DRAG_ICON;
      this.gutter.classList.add('pm-gutter-drag');
    } else {
      this.gutter.textContent = '';
      this.gutter.classList.remove('pm-gutter-drag');
    }
  }

  update(node: ProseMirrorNode): boolean {
    return node.type.name === 'label';
  }

  destroy() {
    this.unsubscribeShift();
  }
}
