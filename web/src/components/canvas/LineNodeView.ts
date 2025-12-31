/**
 * LineNodeView - ProseMirror NodeView for line nodes
 *
 * Features:
 * - Gutter shows line type icon (empty for lyric, # for header, > for chord, // for annotation)
 * - Click on gutter cycles through line types
 * - Drag from gutter to reorder lines
 */

import { Node as ProseMirrorNode, DOMSerializer } from 'prosemirror-model';
import { NodeSelection } from 'prosemirror-state';
import { EditorView, NodeView } from 'prosemirror-view';
import { LineType } from '@/types/song';

import { LINE_TYPE_CYCLE, LINE_TYPE_ICONS } from './constants';

export class LineNodeView implements NodeView {
  dom: HTMLElement;
  contentDOM: HTMLElement;
  private gutter: HTMLElement;
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

    // Create wrapper
    this.dom = document.createElement('div');
    this.dom.className = 'pm-line-wrapper';

    // Create gutter element (drag handle)
    this.gutter = document.createElement('div');
    this.gutter.className = 'pm-gutter';
    this.gutter.contentEditable = 'false';
    this.gutter.draggable = true;
    this.dom.appendChild(this.gutter);

    // Create content area
    this.contentDOM = document.createElement('div');
    this.contentDOM.className = 'pm-line-content';
    this.dom.appendChild(this.contentDOM);

    // Set initial state
    this.updateGutter();

    // Bind event handlers
    this.handleGutterClick = this.handleGutterClick.bind(this);
    this.handleDragStart = this.handleDragStart.bind(this);
    this.gutter.addEventListener('click', this.handleGutterClick);
    this.gutter.addEventListener('dragstart', this.handleDragStart);
  }

  private updateGutter() {
    const lineType = (this.node.attrs.lineType as LineType) || LineType.LYRIC;
    this.dom.setAttribute('data-line-type', lineType);
    this.contentDOM.className = `pm-line-content pm-line-${lineType.toLowerCase()}`;
    this.gutter.textContent = LINE_TYPE_ICONS[lineType];
  }

  private handleDragStart(e: DragEvent) {
    const pos = this.getPos();
    if (pos === undefined || !e.dataTransfer) return;

    const { state } = this.view;
    const lineStart = pos;
    const lineEnd = pos + this.node.nodeSize;

    // Check if there's an existing selection that includes this line
    const { from, to } = state.selection;
    const selectionIncludesThisLine = from < lineEnd && to > lineStart;
    const isMultiLineSelection = !state.selection.empty && (to - from > this.node.nodeSize);

    // If there's a multi-line selection that includes this line, use it
    // Otherwise, select just this line
    if (selectionIncludesThisLine && isMultiLineSelection) {
      // Use existing selection - don't change it
    } else {
      // Select just this node
      const selection = NodeSelection.create(state.doc, pos);
      this.view.dispatch(state.tr.setSelection(selection));
    }

    // Get the current selection (may have been updated above)
    const currentSelection = this.view.state.selection;
    const slice = currentSelection.content();

    // Serialize to HTML for the drag data
    const serializer = DOMSerializer.fromSchema(state.schema);
    const fragment = serializer.serializeFragment(slice.content);
    const div = document.createElement('div');
    div.appendChild(fragment);

    e.dataTransfer.setData('text/html', div.innerHTML);
    e.dataTransfer.setData('text/plain', slice.content.textBetween(0, slice.content.size, '\n'));
    e.dataTransfer.effectAllowed = 'move';
  }

  private handleGutterClick(e: MouseEvent) {
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
    this.gutter.removeEventListener('dragstart', this.handleDragStart);
  }
}
