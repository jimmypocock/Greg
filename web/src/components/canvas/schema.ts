/**
 * ProseMirror Schema for Song Editor
 *
 * Structure:
 *   doc
 *   └── line+ (flat list of lines, each with id and type)
 *
 * Line types: LYRIC, CHORD, ANNOTATION, SECTION_HEADER
 * Sections/parts are external metadata, not document structure.
 */

import { Schema, NodeSpec, MarkSpec } from 'prosemirror-model';
import { LineType } from '@/types/song';

// Node specifications

const doc: NodeSpec = {
  content: 'line+',
};

const line: NodeSpec = {
  content: 'text*',
  attrs: {
    id: { default: null },
    lineType: { default: LineType.LYRIC },
  },
  parseDOM: [
    {
      tag: 'div.line',
      getAttrs: (dom) => {
        const el = dom as HTMLElement;
        return {
          id: el.getAttribute('data-id'),
          lineType: el.getAttribute('data-line-type') || LineType.LYRIC,
        };
      },
    },
  ],
  toDOM: (node) => [
    'div',
    {
      class: `line line-${node.attrs.lineType.toLowerCase()}`,
      'data-id': node.attrs.id,
      'data-line-type': node.attrs.lineType,
    },
    0,
  ],
};

const text: NodeSpec = {
  group: 'inline',
};

// Marks (for future inline formatting)

const marks: { [key: string]: MarkSpec } = {};

// Create schema

export const songSchema = new Schema({
  nodes: {
    doc,
    line,
    text,
  },
  marks,
});

// Helper functions

/**
 * Create an empty document with a single line.
 */
export function createEmptyDoc() {
  return songSchema.node('doc', null, [
    songSchema.node('line', { id: crypto.randomUUID(), lineType: LineType.LYRIC }),
  ]);
}

/**
 * Create a line node.
 */
export function createLine(
  text: string = '',
  lineType: LineType = LineType.LYRIC,
  id: string | null = null
) {
  return songSchema.node(
    'line',
    { id: id || crypto.randomUUID(), lineType },
    text ? [songSchema.text(text)] : []
  );
}

export type { NodeSpec, MarkSpec };
