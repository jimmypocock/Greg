/**
 * Chord Annotations Extension for CodeMirror
 *
 * Renders floating chord labels above text at specific positions.
 * Chords are stored separately from the text and rendered as decorations.
 */

import {
  EditorView,
  Decoration,
  DecorationSet,
  WidgetType,
  ViewPlugin,
  ViewUpdate,
} from '@codemirror/view';
import { StateField, StateEffect, EditorState, Facet } from '@codemirror/state';

// Types
export interface ChordAnnotation {
  /** Line number (0-based) */
  line: number;
  /** Character position within the line */
  position: number;
  /** The chord text (e.g., "Am", "G7", "Cmaj7") */
  chord: string;
}

// State effects for chord operations
export const addChord = StateEffect.define<ChordAnnotation>();
export const removeChord = StateEffect.define<{ line: number; position: number }>();
export const setChords = StateEffect.define<ChordAnnotation[]>();

// Chord widget that renders above text
class ChordWidget extends WidgetType {
  constructor(readonly chord: string) {
    super();
  }

  toDOM() {
    const wrapper = document.createElement('span');
    wrapper.className = 'cm-chord-annotation';
    wrapper.textContent = this.chord;
    wrapper.style.cssText = `
      position: absolute;
      top: -1.4em;
      left: 0;
      font-size: 0.75em;
      font-weight: 500;
      color: var(--song-chord-color, #2563eb);
      background: var(--chord-bg, rgba(37, 99, 235, 0.1));
      padding: 0 4px;
      border-radius: 3px;
      white-space: nowrap;
      pointer-events: auto;
      cursor: pointer;
      z-index: 10;
    `;
    wrapper.title = `Chord: ${this.chord} (click to edit)`;
    return wrapper;
  }

  eq(other: ChordWidget) {
    return other.chord === this.chord;
  }

  ignoreEvent() {
    return false;
  }
}

// State field to store chord annotations
export const chordAnnotationsField = StateField.define<ChordAnnotation[]>({
  create() {
    return [];
  },
  update(chords, tr) {
    for (const effect of tr.effects) {
      if (effect.is(setChords)) {
        return effect.value;
      }
      if (effect.is(addChord)) {
        // Remove any existing chord at same position, then add new one
        const filtered = chords.filter(
          (c) => !(c.line === effect.value.line && c.position === effect.value.position)
        );
        return [...filtered, effect.value].sort((a, b) =>
          a.line === b.line ? a.position - b.position : a.line - b.line
        );
      }
      if (effect.is(removeChord)) {
        return chords.filter(
          (c) => !(c.line === effect.value.line && c.position === effect.value.position)
        );
      }
    }
    // When document changes, we need to update line numbers
    // For simplicity, just keep existing chords (will need smarter mapping for production)
    return chords;
  },
});

// Build decorations from chord annotations
function buildDecorations(state: EditorState): DecorationSet {
  const chords = state.field(chordAnnotationsField);
  const decorations: { from: number; decoration: Decoration }[] = [];

  for (const chord of chords) {
    const line = state.doc.line(chord.line + 1); // Convert 0-based to 1-based
    if (chord.position <= line.length) {
      const pos = line.from + chord.position;
      decorations.push({
        from: pos,
        decoration: Decoration.widget({
          widget: new ChordWidget(chord.chord),
          side: -1, // Render before the character
        }),
      });
    }
  }

  return Decoration.set(
    decorations
      .sort((a, b) => a.from - b.from)
      .map((d) => d.decoration.range(d.from))
  );
}

// View plugin to render decorations
const chordDecorations = ViewPlugin.fromClass(
  class {
    decorations: DecorationSet;

    constructor(view: EditorView) {
      this.decorations = buildDecorations(view.state);
    }

    update(update: ViewUpdate) {
      if (update.docChanged || update.transactions.some((tr) =>
        tr.effects.some((e) => e.is(addChord) || e.is(removeChord) || e.is(setChords))
      )) {
        this.decorations = buildDecorations(update.state);
      }
    }
  },
  {
    decorations: (v) => v.decorations,
  }
);

// Add line height to accommodate chord annotations
const chordLineHeight = EditorView.theme({
  '.cm-line': {
    position: 'relative',
    paddingTop: '1.4em', // Space for chord annotations
  },
  '.cm-chord-annotation': {
    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
  },
});

// Click handler to add/edit chords
const chordClickHandler = EditorView.domEventHandlers({
  click(event, view) {
    // Check if clicked on a chord annotation
    const target = event.target as HTMLElement;
    if (target.classList.contains('cm-chord-annotation')) {
      event.preventDefault();
      const pos = view.posAtDOM(target);
      const line = view.state.doc.lineAt(pos);
      const lineNumber = line.number - 1; // Convert to 0-based
      const position = pos - line.from;

      // For now, just remove on click (will add edit modal later)
      view.dispatch({
        effects: removeChord.of({ line: lineNumber, position }),
      });
      return true;
    }
    return false;
  },
  dblclick(event, view) {
    // Double-click to add chord at position
    const pos = view.posAtCoords({ x: event.clientX, y: event.clientY });
    if (pos !== null) {
      const line = view.state.doc.lineAt(pos);
      const lineNumber = line.number - 1;
      const position = pos - line.from;

      const chord = prompt('Enter chord:');
      if (chord) {
        view.dispatch({
          effects: addChord.of({ line: lineNumber, position, chord }),
        });
      }
      return true;
    }
    return false;
  },
});

// CSS for dark mode
const chordDarkModeStyles = EditorView.theme({
  '.dark &, .dark & .cm-chord-annotation': {
    '--chord-bg': 'rgba(96, 165, 250, 0.15)',
  },
}, { dark: true });

/**
 * Extension bundle for chord annotations.
 * Usage: Add to CodeMirror extensions array.
 */
export function chordAnnotations(initialChords: ChordAnnotation[] = []) {
  return [
    chordAnnotationsField.init(() => initialChords),
    chordDecorations,
    chordLineHeight,
    chordClickHandler,
  ];
}

/**
 * Helper to get current chords from editor state.
 */
export function getChords(state: EditorState): ChordAnnotation[] {
  return state.field(chordAnnotationsField);
}

/**
 * Helper to dispatch chord changes.
 */
export function dispatchSetChords(view: EditorView, chords: ChordAnnotation[]) {
  view.dispatch({ effects: setChords.of(chords) });
}

export function dispatchAddChord(view: EditorView, chord: ChordAnnotation) {
  view.dispatch({ effects: addChord.of(chord) });
}

export function dispatchRemoveChord(view: EditorView, line: number, position: number) {
  view.dispatch({ effects: removeChord.of({ line, position }) });
}
