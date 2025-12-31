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
import { dropCursor } from 'prosemirror-dropcursor';
import { gapCursor } from 'prosemirror-gapcursor';
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

        // Prefix patterns (same as CodeMirror version)
        const chordPattern = /^>\s/;
        const annotationPattern = /^\/\/\s/;
        const sectionPattern = /^#\s/;

        // Debug: log what we see
        console.log('[prefixDetection]', {
          text: JSON.stringify(text),
          currentType,
          matchesChord: chordPattern.test(text),
          matchesAnnotation: annotationPattern.test(text),
          matchesSection: sectionPattern.test(text),
        });

        if (chordPattern.test(text) && currentType !== LineType.CHORD) {
          console.log('[prefixDetection] → changing to CHORD');
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.CHORD });
        } else if (annotationPattern.test(text) && currentType !== LineType.ANNOTATION) {
          console.log('[prefixDetection] → changing to ANNOTATION');
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.ANNOTATION });
        } else if (sectionPattern.test(text) && currentType !== LineType.SECTION_HEADER) {
          console.log('[prefixDetection] → changing to SECTION_HEADER');
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.SECTION_HEADER });
        } else if (
          !chordPattern.test(text) &&
          !annotationPattern.test(text) &&
          !sectionPattern.test(text) &&
          currentType !== LineType.LYRIC
        ) {
          console.log('[prefixDetection] → changing to LYRIC');
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.LYRIC });
        }
      });

      console.log('[prefixDetection] returning transaction:', tr ? 'yes' : 'no');
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
