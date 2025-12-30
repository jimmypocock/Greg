/**
 * Section Controls Extension for CodeMirror
 *
 * Adds inline controls (version, audio, drag handle) to section header lines.
 * Controls appear on hover and allow managing versions, audio, and reordering.
 */

import { StateField, RangeSetBuilder } from '@codemirror/state';
import { EditorView, Decoration, DecorationSet, WidgetType } from '@codemirror/view';
import { LineType } from '@/types/song';
import { lineTypesField, setLineType } from './lineTypes';

// Widget for inline section controls (version, audio, reorder)
class SectionControlsWidget extends WidgetType {
  constructor(readonly lineNumber: number) {
    super();
  }

  eq(other: SectionControlsWidget) {
    return other.lineNumber === this.lineNumber;
  }

  toDOM() {
    const container = document.createElement('span');
    container.className = 'section-inline-controls';
    container.dataset.lineNumber = String(this.lineNumber);

    // Version button
    const versionBtn = document.createElement('button');
    versionBtn.className = 'section-inline-btn section-version-btn';
    versionBtn.textContent = 'v1';
    versionBtn.title = 'Manage versions';
    versionBtn.dataset.action = 'version';
    container.appendChild(versionBtn);

    // Audio button
    const audioBtn = document.createElement('button');
    audioBtn.className = 'section-inline-btn section-audio-btn';
    audioBtn.textContent = '♪';
    audioBtn.title = 'Add/play audio';
    audioBtn.dataset.action = 'audio';
    container.appendChild(audioBtn);

    // Drag handle (far right)
    const dragHandle = document.createElement('span');
    dragHandle.className = 'section-inline-btn section-drag-handle';
    dragHandle.textContent = '⋮⋮';
    dragHandle.title = 'Drag to reorder';
    dragHandle.draggable = true;
    dragHandle.dataset.dragHandle = 'true';
    dragHandle.dataset.lineNumber = String(this.lineNumber);

    // Prevent CodeMirror from capturing mouse events
    dragHandle.onmousedown = (e) => {
      e.stopPropagation();
    };
    dragHandle.ondragstart = (e) => {
      e.stopPropagation();
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', String(this.lineNumber));
      }
      document.body.classList.add('dragging-section');
    };
    dragHandle.ondragend = (e) => {
      e.stopPropagation();
      document.body.classList.remove('dragging-section');
    };
    container.appendChild(dragHandle);

    return container;
  }

  ignoreEvent() {
    return false; // Allow click events
  }
}

// Build section controls decorations
function buildSectionControls(
  state: {
    doc: { lines: number; line: (n: number) => { from: number; to: number } };
    field: (field: StateField<Map<number, LineType>>) => Map<number, LineType>;
  }
): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  const types = state.field(lineTypesField);

  for (let i = 1; i <= state.doc.lines; i++) {
    const lineType = types.get(i) || LineType.LYRIC;
    if (lineType === LineType.SECTION_HEADER) {
      const line = state.doc.line(i);
      // Add widget at the end of the line
      const widget = Decoration.widget({
        widget: new SectionControlsWidget(i),
        side: 1, // After the content
      });
      builder.add(line.to, line.to, widget);
    }
  }

  return builder.finish();
}

// StateField that provides inline section controls
export const sectionControlsDecorations = StateField.define<DecorationSet>({
  create(state) {
    return buildSectionControls(state);
  },
  update(decorations, tr) {
    if (tr.docChanged || tr.effects.some((e) => e.is(setLineType))) {
      return buildSectionControls(tr.state);
    }
    return decorations;
  },
  provide: (field) => EditorView.decorations.from(field),
});

// Helper to find section boundaries (returns { from, to } for the entire section including content)
export function getSectionRange(
  state: {
    doc: { lines: number; line: (n: number) => { from: number; to: number } };
    field: (field: StateField<Map<number, LineType>>) => Map<number, LineType>;
  },
  sectionHeaderLine: number
): { from: number; to: number; includesTrailingNewline: boolean } {
  const types = state.field(lineTypesField);
  const startLine = state.doc.line(sectionHeaderLine);

  // Find the next section header or end of document
  let endLineNum = sectionHeaderLine;
  for (let i = sectionHeaderLine + 1; i <= state.doc.lines; i++) {
    const lineType = types.get(i) || LineType.LYRIC;
    if (lineType === LineType.SECTION_HEADER) {
      break;
    }
    endLineNum = i;
  }

  const endLine = state.doc.line(endLineNum);
  const isLastSection = endLineNum === state.doc.lines;

  return {
    from: startLine.from,
    to: endLine.to,
    includesTrailingNewline: !isLastSection,
  };
}
