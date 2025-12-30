/**
 * Line Types Extension for CodeMirror
 *
 * Manages line type state (lyric, section header, chord, annotation),
 * provides gutter markers for visual indication and click-to-change,
 * and applies line decorations for styling.
 */

import { StateField, StateEffect, RangeSetBuilder } from '@codemirror/state';
import { EditorView, gutter, GutterMarker, Decoration, DecorationSet } from '@codemirror/view';
import { LineType } from '@/types/song';

// Line type icons (match keyboard shortcuts)
export const LINE_ICONS: Record<LineType, string> = {
  [LineType.SECTION_HEADER]: '#',
  [LineType.CHORD]: '>',
  [LineType.ANNOTATION]: '//',
  [LineType.LYRIC]: '',
};

// Line type cycle order (for clicking to change)
export const LINE_TYPE_CYCLE: LineType[] = [
  LineType.LYRIC,
  LineType.SECTION_HEADER,
  LineType.CHORD,
  LineType.ANNOTATION,
];

// State effect to set line type
export const setLineType = StateEffect.define<{ lineNumber: number; type: LineType }>();

// State field to track line types (line number -> LineType)
export const lineTypesField = StateField.define<Map<number, LineType>>({
  create() {
    return new Map();
  },
  update(types, tr) {
    // Handle document changes - shift line numbers as needed
    let newTypes = types;
    if (tr.docChanged) {
      newTypes = new Map();
      const oldDoc = tr.startState.doc;
      const newDoc = tr.newDoc;

      // Track which old line number first mapped to each new line
      // This ensures when lines merge, the FIRST (surviving) line's type wins
      const firstOldLineForNew = new Map<number, number>();

      // Determine which old line each new line came from (process in order)
      for (let oldLineNum = 1; oldLineNum <= oldDoc.lines; oldLineNum++) {
        const oldLine = oldDoc.line(oldLineNum);
        const newPos = tr.changes.mapPos(oldLine.from, -1);
        if (newPos <= newDoc.length) {
          const newLineNum = newDoc.lineAt(newPos).number;
          // Only record the first old line that maps to each new line
          if (!firstOldLineForNew.has(newLineNum)) {
            firstOldLineForNew.set(newLineNum, oldLineNum);
          }
        }
      }

      // For each new line, use the type of the first old line that mapped to it
      for (const [newLineNum, oldLineNum] of firstOldLineForNew) {
        const type = types.get(oldLineNum);
        if (type) {
          newTypes.set(newLineNum, type);
        }
        // If no type, it defaults to LYRIC (no entry needed)
      }
    }

    // Apply any line type changes
    for (const effect of tr.effects) {
      if (effect.is(setLineType)) {
        newTypes = new Map(newTypes);
        newTypes.set(effect.value.lineNumber, effect.value.type);
      }
    }

    return newTypes;
  },
});

// Get line type from state
export function getLineType(
  state: { field: (field: StateField<Map<number, LineType>>) => Map<number, LineType> },
  lineNumber: number
): LineType {
  const types = state.field(lineTypesField);
  return types.get(lineNumber) || LineType.LYRIC;
}

// Export helper to get all line types from editor state
export function getLineTypes(
  state: { field: (field: StateField<Map<number, LineType>>) => Map<number, LineType>; doc: { lines: number } }
): Map<number, LineType> {
  return state.field(lineTypesField);
}

// Gutter marker that's clickable
class LineTypeMarker extends GutterMarker {
  constructor(readonly lineType: LineType) {
    super();
  }

  eq(other: LineTypeMarker) {
    return other.lineType === this.lineType;
  }

  toDOM() {
    const span = document.createElement('span');
    // Don't show icon for lyrics (default type), but keep the clickable area
    if (this.lineType === LineType.LYRIC) {
      span.textContent = ' ';
      span.className = 'line-type-icon line-type-lyric';
      span.title = 'Lyric (click to change)';
    } else {
      span.textContent = LINE_ICONS[this.lineType];
      span.className = `line-type-icon line-type-${this.lineType.toLowerCase()}`;
      span.title = `${this.lineType.replace('_', ' ')} (click to change)`;
    }
    return span;
  }
}

// Create markers for each type
const markers: Record<LineType, LineTypeMarker> = {
  [LineType.LYRIC]: new LineTypeMarker(LineType.LYRIC),
  [LineType.SECTION_HEADER]: new LineTypeMarker(LineType.SECTION_HEADER),
  [LineType.CHORD]: new LineTypeMarker(LineType.CHORD),
  [LineType.ANNOTATION]: new LineTypeMarker(LineType.ANNOTATION),
};

// Gutter that shows clickable line type icons
export const lineTypeGutter = gutter({
  class: 'cm-lineType-gutter',
  markers: (view) => {
    const builder = new RangeSetBuilder<GutterMarker>();

    for (const { from, to } of view.visibleRanges) {
      for (let pos = from; pos <= to; ) {
        const line = view.state.doc.lineAt(pos);
        const lineType = getLineType(view.state, line.number);
        builder.add(line.from, line.from, markers[lineType]);
        pos = line.to + 1;
      }
    }

    return builder.finish();
  },
  domEventHandlers: {
    click: (view, line) => {
      const lineNumber = view.state.doc.lineAt(line.from).number;
      const currentType = getLineType(view.state, lineNumber);
      const currentIndex = LINE_TYPE_CYCLE.indexOf(currentType);
      const nextIndex = (currentIndex + 1) % LINE_TYPE_CYCLE.length;
      const nextType = LINE_TYPE_CYCLE[nextIndex];

      view.dispatch({
        effects: setLineType.of({ lineNumber, type: nextType }),
      });

      return true;
    },
  },
});

// Line decorations for styling each line type
const lineDecorations: Record<LineType, Decoration> = {
  [LineType.LYRIC]: Decoration.line({ class: 'cm-line-lyric' }),
  [LineType.SECTION_HEADER]: Decoration.line({ class: 'cm-line-section' }),
  [LineType.CHORD]: Decoration.line({ class: 'cm-line-chord' }),
  [LineType.ANNOTATION]: Decoration.line({ class: 'cm-line-annotation' }),
};

// Build line decorations based on line types
function buildLineDecorations(
  state: {
    doc: { lines: number; line: (n: number) => { from: number } };
    field: (field: StateField<Map<number, LineType>>) => Map<number, LineType>;
  }
): DecorationSet {
  const builder = new RangeSetBuilder<Decoration>();
  const types = state.field(lineTypesField);

  for (let i = 1; i <= state.doc.lines; i++) {
    const lineType = types.get(i) || LineType.LYRIC;
    const line = state.doc.line(i);
    builder.add(line.from, line.from, lineDecorations[lineType]);
  }

  return builder.finish();
}

// StateField that provides line decorations based on line types
export const lineTypeDecorations = StateField.define<DecorationSet>({
  create(state) {
    return buildLineDecorations(state);
  },
  update(decorations, tr) {
    if (tr.docChanged || tr.effects.some((e) => e.is(setLineType))) {
      return buildLineDecorations(tr.state);
    }
    return decorations;
  },
  provide: (field) => EditorView.decorations.from(field),
});
