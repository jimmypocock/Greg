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
import { EditorState, Transaction, Plugin, PluginKey, TextSelection } from 'prosemirror-state';
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
 * When # is typed, creates a new part (section) instead of just changing line type.
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
      const chordPattern = /^>\s/;
      const annotationPattern = /^\/\/\s/;
      const sectionPattern = /^#\s/;

      // First pass: find ONE line that needs to become a new part
      // (Process only one at a time to avoid position mapping complexity)
      let foundLinePos = -1;
      let foundLineText = '';
      let foundPartPos = -1;
      let foundPartNode: ProseMirrorNode | null = null;

      // First, collect all parts and their positions
      const parts: Array<{ node: ProseMirrorNode; pos: number; endPos: number }> = [];
      newState.doc.forEach((child, offset) => {
        if (child.type.name === 'part') {
          parts.push({
            node: child,
            pos: offset,
            endPos: offset + child.nodeSize,
          });
        }
      });

      // Find # lines that need to become new parts
      newState.doc.descendants((node, pos) => {
        if (foundLinePos >= 0) return false; // Stop after finding one
        if (node.type.name !== 'line') return;

        const text = node.textContent;

        // If line starts with "# " (hash space), mark for conversion to part
        if (sectionPattern.test(text)) {
          // Find the parent part by checking which part contains this position
          const parentPart = parts.find((p) => pos >= p.pos && pos < p.endPos);
          if (parentPart) {
            foundLinePos = pos;
            foundLineText = text;
            foundPartPos = parentPart.pos;
            foundPartNode = parentPart.node;
            return false; // Stop iteration
          }
        }
      });

      // Convert the # line to a new part
      if (foundLinePos >= 0 && foundPartNode !== null) {
        const pos = foundLinePos;
        const partPos = foundPartPos;
        const partNode: ProseMirrorNode = foundPartNode;

        // Get label text (remove "# " prefix)
        const labelText = foundLineText.replace(/^#\s/, '');

        // Find the index of this line within the part
        let lineIndex = -1;
        partNode.forEach((child, offset, index) => {
          if (lineIndex === -1) {
            const childPos = partPos + 1 + offset;
            if (childPos === pos) {
              lineIndex = index;
            }
          }
        });

        // Validate we found the line
        if (lineIndex === -1) {
          console.warn('[prefixDetection] Could not find line in parent part');
        } else {
          // Skip if this is the first line (index 1, after label) of a new part with empty label
          // This prevents infinite loops when we create new parts
          const isFirstLine = lineIndex === 1;
          const labelNode = partNode.firstChild;
          const hasEmptyLabel = labelNode?.textContent === '';

          if (isFirstLine && hasEmptyLabel) {
            // Don't convert - this is likely a newly created part
          } else {
            // Collect lines that should move to the new part (lines after the # line)
            const linesToMove: ProseMirrorNode[] = [];
            let passedTargetLine = false;

            partNode.forEach((child, offset, index) => {
              if (index === lineIndex) {
                passedTargetLine = true;
              } else if (passedTargetLine && child.type.name === 'line') {
                linesToMove.push(child);
              }
            });

            // Create the new part
            const newPartId = crypto.randomUUID();
            const newPartLines = linesToMove.length > 0
              ? linesToMove
              : [songSchema.node('line', { lineType: LineType.LYRIC }, [])];

            const newPart = songSchema.node(
              'part',
              { id: newPartId, type: SectionType.VERSE, mainVersionId: null },
              [
                songSchema.node('label', null, labelText ? [songSchema.text(labelText)] : []),
                ...newPartLines,
              ]
            );

            // Calculate what to delete: from the # line to end of part content
            const deleteFrom = pos;
            const deleteTo = partPos + partNode.nodeSize - 1;

            tr = newState.tr;

            // Delete the # line and everything after it
            tr.delete(deleteFrom, deleteTo);

            // The part has shrunk - calculate new insert position (right after the modified part)
            const deletedAmount = deleteTo - deleteFrom;
            const insertAt = partPos + partNode.nodeSize - deletedAmount;

            // Insert the new part
            tr.insert(insertAt, newPart);

            // Position cursor at the start of the new part's first line
            // The new part starts at insertAt, label is at insertAt+1, first line is after label
            const labelSize = newPart.child(0).nodeSize;
            const cursorPos = insertAt + 1 + labelSize + 1; // inside first line
            tr.setSelection(TextSelection.near(tr.doc.resolve(cursorPos)));
          }
        }
      }

      // Second pass: handle chord and annotation line types (only if we didn't create parts)
      if (!tr) {
        newState.doc.descendants((node, pos) => {
          if (node.type.name !== 'line') return;

          const text = node.textContent;
          const currentType = node.attrs.lineType;

          if (chordPattern.test(text) && currentType !== LineType.CHORD) {
            if (!tr) tr = newState.tr;
            tr.setNodeMarkup(pos, undefined, { lineType: LineType.CHORD });
          } else if (annotationPattern.test(text) && currentType !== LineType.ANNOTATION) {
            if (!tr) tr = newState.tr;
            tr.setNodeMarkup(pos, undefined, { lineType: LineType.ANNOTATION });
          } else if (
            !chordPattern.test(text) &&
            !annotationPattern.test(text) &&
            !sectionPattern.test(text) &&
            currentType !== LineType.LYRIC
          ) {
            if (!tr) tr = newState.tr;
            tr.setNodeMarkup(pos, undefined, { lineType: LineType.LYRIC });
          }
        });
      }

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
