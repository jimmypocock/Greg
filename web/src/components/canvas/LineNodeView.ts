/**
 * LineNodeView - ProseMirror NodeView for line nodes
 *
 * Features:
 * - Gutter shows line type icon (empty for lyric, # for header, > for chord, // for annotation)
 * - Click on gutter cycles through line types
 * - When Shift is held, gutter shows drag icon and enables dragging
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { NodeSelection } from 'prosemirror-state';
import { EditorView, NodeView } from 'prosemirror-view';
import { LineType } from '@/types/song';

import { LINE_TYPE_CYCLE, LINE_TYPE_ICONS, DRAG_ICON } from './constants';
import { getIsShiftHeld, subscribeToShift } from './shiftTracking';

export class LineNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;
  private gutter: HTMLElement;
  private node: ProseMirrorNode;
  private view: EditorView;
  private getPos: () => number | undefined;
  private unsubscribeShift: () => void;

  constructor(
    node: ProseMirrorNode,
    view: EditorView,
    getPos: () => number | undefined
  ) {
    this.node = node;
    this.view = view;
    this.getPos = getPos;

    // Create wrapper
    this.dom = document.createElement('div');
    this.dom.className = 'pm-line-wrapper';

    // Create gutter element (acts as drag handle when shift is held)
    this.gutter = document.createElement('div');
    this.gutter.className = 'pm-gutter';
    this.gutter.contentEditable = 'false';
    this.dom.appendChild(this.gutter);

    // Create content area
    this.contentDOM = document.createElement('div');
    this.contentDOM.className = 'pm-line-content';
    this.dom.appendChild(this.contentDOM);

    // Set initial state
    this.updateGutter();

    // Bind event handlers
    this.handleGutterClick = this.handleGutterClick.bind(this);
    this.handleGutterMouseDown = this.handleGutterMouseDown.bind(this);
    this.gutter.addEventListener('click', this.handleGutterClick);
    this.gutter.addEventListener('mousedown', this.handleGutterMouseDown);

    // Subscribe to shift key changes
    this.unsubscribeShift = subscribeToShift(() => this.updateGutter());
  }

  private updateGutter() {
    const lineType = (this.node.attrs.lineType as LineType) || LineType.LYRIC;
    this.dom.setAttribute('data-line-type', lineType);
    this.contentDOM.className = `pm-line-content pm-line-${lineType.toLowerCase()}`;

    // Show drag icon and enable dragging when shift is held
    if (getIsShiftHeld()) {
      this.gutter.textContent = DRAG_ICON;
      this.gutter.classList.add('pm-gutter-drag');
      this.gutter.draggable = true;
    } else {
      this.gutter.textContent = LINE_TYPE_ICONS[lineType];
      this.gutter.classList.remove('pm-gutter-drag');
      this.gutter.draggable = false;
    }
  }

  private handleGutterMouseDown(e: MouseEvent) {
    // If shift is held, let the drag happen (don't prevent default)
    if (getIsShiftHeld()) {
      // Select the node so ProseMirror knows what to drag
      const pos = this.getPos();
      if (pos !== undefined) {
        const { state } = this.view;
        const selection = NodeSelection.create(state.doc, pos);
        this.view.dispatch(state.tr.setSelection(selection));
      }
      return; // Let the drag proceed
    }
  }

  private handleGutterClick(e: MouseEvent) {
    // Don't cycle line types if shift is held (drag mode)
    if (getIsShiftHeld()) {
      return;
    }

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
  }

  update(node: ProseMirrorNode): boolean {
    if (node.type !== this.node.type) return false;
    this.node = node;
    this.updateGutter();
    return true;
  }

  destroy() {
    this.gutter.removeEventListener('click', this.handleGutterClick);
    this.gutter.removeEventListener('mousedown', this.handleGutterMouseDown);
    this.unsubscribeShift();
  }
}
