/**
 * ProseMirror Plugins for Song Editor
 *
 * - Prefix detection (> for chord, // for annotation)
 * - Line type styling
 */

import { Plugin, PluginKey, Transaction } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import { LineType } from '@/types/song';
import { songSchema } from './schema';

const prefixPluginKey = new PluginKey('prefixDetection');

/**
 * Plugin to detect prefix typing and convert line types.
 *
 * When user types "> " or "// " at the start of a line,
 * automatically set the lineType attribute.
 */
export function prefixDetectionPlugin() {
  return new Plugin({
    key: prefixPluginKey,

    appendTransaction(transactions, oldState, newState) {
      // Only check if there were document changes
      if (!transactions.some((tr) => tr.docChanged)) {
        return null;
      }

      let tr: Transaction | null = null;

      newState.doc.descendants((node, pos) => {
        if (node.type.name !== 'line') return;

        const text = node.textContent;
        const currentType = node.attrs.lineType;

        // Check for chord prefix
        if (text.startsWith('> ') && currentType !== LineType.CHORD) {
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.CHORD });
        }
        // Check for annotation prefix
        else if (text.startsWith('// ') && currentType !== LineType.ANNOTATION) {
          if (!tr) tr = newState.tr;
          tr.setNodeMarkup(pos, undefined, { lineType: LineType.ANNOTATION });
        }
        // Reset to lyric if prefix removed
        else if (
          !text.startsWith('> ') &&
          !text.startsWith('// ') &&
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

const decorationPluginKey = new PluginKey('lineDecorations');

/**
 * Plugin to add decorations for line types and hidden prefixes.
 */
export function lineDecorationPlugin() {
  return new Plugin({
    key: decorationPluginKey,

    props: {
      decorations(state) {
        const decorations: Decoration[] = [];

        state.doc.descendants((node, pos) => {
          if (node.type.name !== 'line') return;

          const lineType = node.attrs.lineType;
          const text = node.textContent;

          // Add class decoration to the line wrapper
          decorations.push(
            Decoration.node(pos, pos + node.nodeSize, {
              class: `line-type-${lineType.toLowerCase()}`,
            })
          );

          // Hide the prefix in the text (but keep it in the document)
          if (lineType === LineType.CHORD && text.startsWith('> ')) {
            decorations.push(
              Decoration.inline(pos + 1, pos + 3, {
                class: 'hidden-prefix',
              })
            );
          } else if (lineType === LineType.ANNOTATION && text.startsWith('// ')) {
            decorations.push(
              Decoration.inline(pos + 1, pos + 4, {
                class: 'hidden-prefix',
              })
            );
          }
        });

        return DecorationSet.create(state.doc, decorations);
      },
    },
  });
}

/**
 * Plugin to handle drop events for part reordering.
 */
export function partDragDropPlugin() {
  return new Plugin({
    props: {
      handleDrop(view, event, slice, moved) {
        // Let ProseMirror handle the drop naturally for now
        // The schema's draggable: true on parts enables this
        return false;
      },
    },
  });
}
