/**
 * ProseMirror Schema for Song Editor
 *
 * Structure:
 *   doc
 *   └── part+ (id, type, mainVersionId)
 *       ├── label (the part's name: "Verse 1", "Chorus", etc.)
 *       └── line* (lyrics, chords, annotations)
 */

import { Schema, NodeSpec, MarkSpec } from 'prosemirror-model';
import { SectionType, LineType } from '@/types/song';

// Node specifications

const doc: NodeSpec = {
  content: 'part+',
};

const part: NodeSpec = {
  content: 'label? line+',
  attrs: {
    id: { default: null },
    type: { default: SectionType.VERSE },
    mainVersionId: { default: null },
  },
  draggable: true,
  parseDOM: [
    {
      tag: 'div.part',
      getAttrs: (dom) => {
        const el = dom as HTMLElement;
        return {
          id: el.getAttribute('data-id'),
          type: el.getAttribute('data-type') || SectionType.VERSE,
          mainVersionId: el.getAttribute('data-main-version-id'),
        };
      },
    },
  ],
  toDOM: (node) => [
    'div',
    {
      class: `part part-${node.attrs.type.toLowerCase()}`,
      'data-id': node.attrs.id,
      'data-type': node.attrs.type,
      'data-main-version-id': node.attrs.mainVersionId,
    },
    0,
  ],
};

const label: NodeSpec = {
  content: 'text*',
  parseDOM: [{ tag: 'div.part-label' }],
  toDOM: () => ['div', { class: 'part-label' }, 0],
};

const line: NodeSpec = {
  content: 'text*',
  draggable: true,
  attrs: {
    lineType: { default: LineType.LYRIC },
  },
  parseDOM: [
    {
      tag: 'div.line',
      getAttrs: (dom) => {
        const el = dom as HTMLElement;
        return {
          lineType: el.getAttribute('data-line-type') || LineType.LYRIC,
        };
      },
    },
  ],
  toDOM: (node) => [
    'div',
    {
      class: `line line-${node.attrs.lineType.toLowerCase()}`,
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
    part,
    label,
    line,
    text,
  },
  marks,
});

// Helper functions

/**
 * Create an empty document with a single part.
 */
export function createEmptyDoc() {
  const id = crypto.randomUUID();
  return songSchema.node('doc', null, [
    songSchema.node('part', { id, type: SectionType.VERSE, mainVersionId: null }, [
      songSchema.node('line', { lineType: LineType.LYRIC }),
    ]),
  ]);
}

/**
 * Create a part node with given content.
 */
export function createPart(
  label: string | null = null,
  type: SectionType = SectionType.VERSE,
  lines: Array<{ text: string; lineType: LineType }> = []
) {
  const id = crypto.randomUUID();
  const lineNodes =
    lines.length > 0
      ? lines.map((l) =>
          songSchema.node(
            'line',
            { lineType: l.lineType },
            l.text ? [songSchema.text(l.text)] : []
          )
        )
      : [songSchema.node('line', { lineType: LineType.LYRIC })];

  const children = label
    ? [songSchema.node('label', null, [songSchema.text(label)]), ...lineNodes]
    : lineNodes;

  return songSchema.node('part', { id, type, mainVersionId: null }, children);
}

export type { NodeSpec, MarkSpec };
