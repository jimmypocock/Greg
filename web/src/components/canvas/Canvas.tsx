'use client';

/**
 * Canvas - Song Editor
 *
 * A flat line-based editor using ProseMirror.
 *
 * Features:
 * - NodeView-based gutters (perfect alignment, handles line wrapping)
 * - Line type cycling via gutter click
 * - Prefix shortcuts: # header, > chord, // annotation
 * - Real-time collaboration via Yjs
 * - Flat structure: doc → line+ (sections are external metadata)
 */

import { useEffect, useRef } from 'react';
import { EditorState, Transaction, Plugin, PluginKey } from 'prosemirror-state';
import { EditorView, Decoration, DecorationSet } from 'prosemirror-view';
import { Node as ProseMirrorNode, Slice, Fragment, ResolvedPos } from 'prosemirror-model';
import { keymap } from 'prosemirror-keymap';
import { baseKeymap } from 'prosemirror-commands';
import { dropCursor } from 'prosemirror-dropcursor';
import { gapCursor } from 'prosemirror-gapcursor';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { ySyncPlugin, yUndoPlugin, undo, redo, initProseMirrorDoc } from 'y-prosemirror';

import { songSchema, createEmptyDoc } from './schema';
import { createNodeViews } from './nodeViews';
import { Song, LineType } from '@/types/song';
import './canvas.css';

interface CanvasProps {
  song: Song;
  onChange?: (doc: ProseMirrorNode) => void;
  onSave?: (doc: ProseMirrorNode) => void;
  // Yjs collaborative editing
  yXmlFragment?: Y.XmlFragment | null;
  provider?: WebsocketProvider | null;
  // Callbacks (not yet wired up)
  onDuplicateVersion?: (partId: string, versionId: string) => Promise<void>;
  onSwitchVersion?: (partId: string, versionId: string) => Promise<void>;
  onUploadAudio?: (partId: string, versionId: string, file: File) => Promise<void>;
  onReorderParts?: (partIds: string[]) => Promise<void>;
}

/**
 * Convert a Song object to ProseMirror document.
 * Creates a flat list of lines - sections become header lines.
 */
function songToDoc(song: Song): ProseMirrorNode {
  if (song.sections.length === 0) {
    return createEmptyDoc();
  }

  const allLines: ProseMirrorNode[] = [];

  song.sections.forEach((section) => {
    // Create section header line
    const labelText =
      section.type.replace('_', ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()) +
      (section.number ? ` ${section.number}` : '');

    if (labelText) {
      allLines.push(
        songSchema.node(
          'line',
          { id: crypto.randomUUID(), lineType: LineType.SECTION_HEADER },
          [songSchema.text('# ' + labelText)]
        )
      );
    }

    // Create content lines
    section.lines.forEach((line) => {
      let text = line.text;
      if (line.line_type === LineType.CHORD && !text.startsWith('> ')) {
        text = '> ' + text;
      } else if (line.line_type === LineType.ANNOTATION && !text.startsWith('// ')) {
        text = '// ' + text;
      } else if (line.line_type === LineType.SECTION_HEADER && !text.startsWith('# ')) {
        text = '# ' + text;
      }

      allLines.push(
        songSchema.node(
          'line',
          { id: line.id || crypto.randomUUID(), lineType: line.line_type },
          text ? [songSchema.text(text)] : []
        )
      );
    });
  });

  // Ensure at least one line
  if (allLines.length === 0) {
    return createEmptyDoc();
  }

  return songSchema.node('doc', null, allLines);
}

/**
 * Plugin to detect prefix typing and convert line types.
 * Also assigns IDs to new lines that don't have them.
 */
function prefixDetectionPlugin() {
  return new Plugin({
    key: new PluginKey('prefixDetection'),

    appendTransaction(transactions, oldState, newState) {
      if (!transactions.some((tr) => tr.docChanged)) {
        return null;
      }

      let tr: Transaction | null = null;

      // Prefix patterns
      const headerPattern = /^#\s/;
      const chordPattern = /^>\s/;
      const annotationPattern = /^\/\/\s/;

      newState.doc.descendants((node, pos) => {
        if (node.type.name !== 'line') return;

        const text = node.textContent;
        const currentType = node.attrs.lineType;
        const currentId = node.attrs.id;

        // Track what needs to change
        let newAttrs: { id?: string; lineType?: LineType } | null = null;

        // Assign ID if missing
        if (!currentId) {
          newAttrs = { id: crypto.randomUUID() };
        }

        // Detect line type from prefix
        if (headerPattern.test(text) && currentType !== LineType.SECTION_HEADER) {
          newAttrs = { ...newAttrs, lineType: LineType.SECTION_HEADER };
        } else if (chordPattern.test(text) && currentType !== LineType.CHORD) {
          newAttrs = { ...newAttrs, lineType: LineType.CHORD };
        } else if (annotationPattern.test(text) && currentType !== LineType.ANNOTATION) {
          newAttrs = { ...newAttrs, lineType: LineType.ANNOTATION };
        } else if (
          !headerPattern.test(text) &&
          !chordPattern.test(text) &&
          !annotationPattern.test(text) &&
          currentType !== LineType.LYRIC
        ) {
          newAttrs = { ...newAttrs, lineType: LineType.LYRIC };
        }

        // Apply changes if needed
        if (newAttrs) {
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { ...node.attrs, ...newAttrs });
        }
      });

      return tr;
    },
  });
}

/**
 * Plugin to hide prefix characters visually.
 * Checks text patterns directly (not lineType attribute) so it works
 * immediately when text is typed, before appendTransaction updates the attribute.
 */
function hidePrefixPlugin() {
  const chordPattern = /^>\s/;
  const annotationPattern = /^\/\/\s/;
  const sectionPattern = /^#\s/;

  return new Plugin({
    key: new PluginKey('hidePrefix'),

    props: {
      decorations(state) {
        const decorations: Decoration[] = [];

        state.doc.descendants((node, pos) => {
          if (node.type.name !== 'line') return;

          const text = node.textContent;

          // Hide prefix based on text pattern (not lineType attribute)
          if (chordPattern.test(text)) {
            decorations.push(
              Decoration.inline(pos + 1, pos + 3, { class: 'pm-hidden-prefix' })
            );
          } else if (annotationPattern.test(text)) {
            decorations.push(
              Decoration.inline(pos + 1, pos + 4, { class: 'pm-hidden-prefix' })
            );
          } else if (sectionPattern.test(text)) {
            decorations.push(
              Decoration.inline(pos + 1, pos + 3, { class: 'pm-hidden-prefix' })
            );
          }
        });

        return DecorationSet.create(state.doc, decorations);
      },
    },
  });
}

/**
 * Parse pasted plain text into proper line nodes.
 * Splits text by newlines and creates a line node for each.
 */
function clipboardTextParser(
  text: string,
  _$context: ResolvedPos,
  _plain: boolean,
  _view: EditorView
): Slice {
  const lines = text.split(/\r?\n/);

  const lineNodes = lines.map((lineText) => {
    // Determine line type based on prefix
    let lineType = LineType.LYRIC;
    if (/^#\s/.test(lineText)) {
      lineType = LineType.SECTION_HEADER;
    } else if (/^>\s/.test(lineText)) {
      lineType = LineType.CHORD;
    } else if (/^\/\/\s/.test(lineText)) {
      lineType = LineType.ANNOTATION;
    }

    return songSchema.node(
      'line',
      { id: crypto.randomUUID(), lineType },
      lineText ? [songSchema.text(lineText)] : []
    );
  });

  return new Slice(Fragment.from(lineNodes), 0, 0);
}

export function Canvas({
  song,
  onChange,
  onSave,
  yXmlFragment,
  provider,
}: CanvasProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  // Use refs for values that shouldn't trigger effect re-runs
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const isCollaborative = !!(yXmlFragment && provider);

  // Create the editor - only when song.id or yXmlFragment changes
  useEffect(() => {
    if (!editorRef.current || !yXmlFragment) return;

    // Initialize ProseMirror doc from the Yjs XmlFragment (per y-prosemirror docs)
    // This reads existing content and creates the mapping for sync
    const { doc, mapping } = initProseMirrorDoc(yXmlFragment, songSchema);

    const plugins = [
      keymap({
        'Mod-z': undo,
        'Mod-y': redo,
        'Mod-Shift-z': redo,
      }),
      keymap(baseKeymap),
      prefixDetectionPlugin(),
      hidePrefixPlugin(),
      dropCursor(),
      gapCursor(),
      ySyncPlugin(yXmlFragment, { mapping }),
      yUndoPlugin(),
    ];

    const state = EditorState.create({
      doc,
      schema: songSchema,
      plugins,
    });

    const view = new EditorView(editorRef.current, {
      state,
      nodeViews: createNodeViews(),
      clipboardTextParser,
      dispatchTransaction(tr) {
        if (!viewRef.current) return;

        const newState = viewRef.current.state.apply(tr);
        viewRef.current.updateState(newState);

        if (tr.docChanged && onChangeRef.current) {
          onChangeRef.current(newState.doc);
        }
      },
      attributes: {
        class: 'pm-editor',
        'aria-label': 'Song editor',
        spellcheck: 'false',
      },
    });

    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, [song.id, yXmlFragment]);  // Only recreate when song or fragment changes

  // Cmd/Ctrl+S to save
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        if (viewRef.current && onSave) {
          onSave(viewRef.current.state.doc);
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onSave]);

  return (
    <div className="pm-canvas">
      {/* Header hints */}
      <div className="pm-hints">
        <span>
          <code>#</code> section
        </span>
        <span>
          <code>&gt;</code> chord
        </span>
        <span>
          <code>//</code> note
        </span>
      </div>

      {/* Editor */}
      <div ref={editorRef} className="pm-editor-container" />
    </div>
  );
}
