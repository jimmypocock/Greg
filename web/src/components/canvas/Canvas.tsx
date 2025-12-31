'use client';

/**
 * Canvas - Song Editor
 *
 * A blank canvas editor using ProseMirror's block structure for stable part IDs.
 *
 * Features:
 * - NodeView-based gutters (perfect alignment, handles line wrapping)
 * - Line type cycling via gutter click
 * - Prefix shortcuts: # section, > chord, // annotation
 * - Real-time collaboration via Yjs
 */

import { useEffect, useRef } from 'react';
import { EditorState, Transaction, Plugin, PluginKey } from 'prosemirror-state';
import { EditorView, Decoration, DecorationSet } from 'prosemirror-view';
import { Node as ProseMirrorNode } from 'prosemirror-model';
import { history } from 'prosemirror-history';
import { keymap } from 'prosemirror-keymap';
import { baseKeymap } from 'prosemirror-commands';
import { TextSelection } from 'prosemirror-state';
import { dropCursor } from 'prosemirror-dropcursor';
import { gapCursor } from 'prosemirror-gapcursor';
import { InputRule, inputRules } from 'prosemirror-inputrules';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { ySyncPlugin, yUndoPlugin, initProseMirrorDoc } from 'y-prosemirror';

import { songSchema, createEmptyDoc } from './schema';
import { createNodeViews } from './nodeViews';
import { Song, SectionType, LineType } from '@/types/song';
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
 */
function songToDoc(song: Song): ProseMirrorNode {
  if (song.sections.length === 0) {
    return createEmptyDoc();
  }

  const parts = song.sections.map((section) => {
    const labelText =
      section.type.replace('_', ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()) +
      (section.number ? ` ${section.number}` : '');

    const lines = section.lines.map((line) => {
      let text = line.text;
      if (line.line_type === LineType.CHORD && !text.startsWith('> ')) {
        text = '> ' + text;
      } else if (line.line_type === LineType.ANNOTATION && !text.startsWith('// ')) {
        text = '// ' + text;
      }

      return songSchema.node(
        'line',
        { lineType: line.line_type },
        text ? [songSchema.text(text)] : []
      );
    });

    const lineNodes =
      lines.length > 0
        ? lines
        : [songSchema.node('line', { lineType: LineType.LYRIC })];

    return songSchema.node(
      'part',
      {
        id: section.id,
        type: section.type,
        mainVersionId: section.main_version_id,
      },
      [
        songSchema.node('label', null, labelText ? [songSchema.text(labelText)] : []),
        ...lineNodes,
      ]
    );
  });

  return songSchema.node('doc', null, parts);
}

/**
 * InputRules for immediate prefix detection.
 * Triggers when user types space after a prefix symbol.
 * Re-inserts the matched text to preserve it.
 */
function createPrefixInputRules() {
  // Rule: typing "# " at start of line → SECTION_HEADER
  const sectionRule = new InputRule(/^#\s$/, (state, match, start, end) => {
    const $pos = state.doc.resolve(start);
    const node = $pos.parent;
    if (node.type.name !== 'line') return null;

    const linePos = $pos.before($pos.depth);
    // Re-insert matched text, then set node markup
    const tr = state.tr
      .insertText(match[0], start, end)
      .setNodeMarkup(linePos, undefined, { lineType: LineType.SECTION_HEADER });
    return tr;
  });

  // Rule: typing "> " at start of line → CHORD
  const chordRule = new InputRule(/^>\s$/, (state, match, start, end) => {
    const $pos = state.doc.resolve(start);
    const node = $pos.parent;
    if (node.type.name !== 'line') return null;

    const linePos = $pos.before($pos.depth);
    const tr = state.tr
      .insertText(match[0], start, end)
      .setNodeMarkup(linePos, undefined, { lineType: LineType.CHORD });
    return tr;
  });

  // Rule: typing "// " at start of line → ANNOTATION
  const annotationRule = new InputRule(/^\/\/\s$/, (state, match, start, end) => {
    const $pos = state.doc.resolve(start);
    const node = $pos.parent;
    if (node.type.name !== 'line') return null;

    const linePos = $pos.before($pos.depth);
    const tr = state.tr
      .insertText(match[0], start, end)
      .setNodeMarkup(linePos, undefined, { lineType: LineType.ANNOTATION });
    return tr;
  });

  return inputRules({ rules: [sectionRule, chordRule, annotationRule] });
}

/**
 * Plugin to detect prefix typing and convert line types.
 */
function prefixDetectionPlugin() {
  return new Plugin({
    key: new PluginKey('prefixDetection'),

    appendTransaction(transactions, oldState, newState) {
      if (!transactions.some((tr) => tr.docChanged)) {
        return null;
      }

      let tr: Transaction | null = null;

      newState.doc.descendants((node, pos) => {
        if (node.type.name !== 'line') return;

        const text = node.textContent;
        const currentType = node.attrs.lineType;

        if (text.startsWith('> ') && currentType !== LineType.CHORD) {
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.CHORD });
        } else if (text.startsWith('// ') && currentType !== LineType.ANNOTATION) {
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.ANNOTATION });
        } else if (text.startsWith('# ') && currentType !== LineType.SECTION_HEADER) {
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.SECTION_HEADER });
        } else if (
          !text.startsWith('> ') &&
          !text.startsWith('// ') &&
          !text.startsWith('# ') &&
          currentType !== LineType.LYRIC
        ) {
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.LYRIC });
        }
      });

      return tr;
    },
  });
}

/**
 * Plugin to hide prefix characters visually.
 */
function hidePrefixPlugin() {
  return new Plugin({
    key: new PluginKey('hidePrefix'),

    props: {
      decorations(state) {
        const decorations: Decoration[] = [];

        state.doc.descendants((node, pos) => {
          if (node.type.name !== 'line') return;

          const lineType = node.attrs.lineType as LineType;
          const text = node.textContent;

          // Hide prefix in text
          if (lineType === LineType.CHORD && text.startsWith('> ')) {
            decorations.push(
              Decoration.inline(pos + 1, pos + 3, { class: 'pm-hidden-prefix' })
            );
          } else if (lineType === LineType.ANNOTATION && text.startsWith('// ')) {
            decorations.push(
              Decoration.inline(pos + 1, pos + 4, { class: 'pm-hidden-prefix' })
            );
          } else if (lineType === LineType.SECTION_HEADER && text.startsWith('# ')) {
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
      keymap(baseKeymap),
      createPrefixInputRules(),
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
