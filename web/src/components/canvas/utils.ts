/**
 * ProseMirror Utilities
 *
 * Conversion between ProseMirror documents and API data structures.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { LineType, SectionType, CanvasSection, CanvasLine } from '@/types/song';

/**
 * Part data extracted from ProseMirror document.
 */
export interface PartData {
  id: string;
  type: SectionType;
  mainVersionId: string | null;
  label: string;
  lines: Array<{
    text: string;
    lineType: LineType;
  }>;
}

/**
 * Extract part data from a ProseMirror document.
 */
export function docToParts(doc: ProseMirrorNode): PartData[] {
  const parts: PartData[] = [];

  doc.forEach((partNode) => {
    if (partNode.type.name !== 'part') return;

    const part: PartData = {
      id: partNode.attrs.id,
      type: partNode.attrs.type,
      mainVersionId: partNode.attrs.mainVersionId,
      label: '',
      lines: [],
    };

    partNode.forEach((child) => {
      if (child.type.name === 'label') {
        part.label = child.textContent;
      } else if (child.type.name === 'line') {
        let text = child.textContent;
        const lineType = child.attrs.lineType as LineType;

        // Remove prefix from text for storage (prefix is just for editing)
        if (lineType === LineType.CHORD && text.startsWith('> ')) {
          text = text.slice(2);
        } else if (lineType === LineType.ANNOTATION && text.startsWith('// ')) {
          text = text.slice(3);
        }

        part.lines.push({ text, lineType });
      }
    });

    parts.push(part);
  });

  return parts;
}

/**
 * Convert ProseMirror document to canvas save format.
 */
export function docToCanvasSections(doc: ProseMirrorNode): CanvasSection[] {
  const parts = docToParts(doc);

  return parts.map((part) => ({
    type: part.type,
    number: undefined, // We don't track number anymore, just label
    lines: part.lines.map((line) => ({
      text: line.text,
      line_type: line.lineType,
      chords: [], // Chords handled separately
    })),
  }));
}

/**
 * Get raw text content from document (for search/export).
 */
export function docToText(doc: ProseMirrorNode): string {
  const lines: string[] = [];

  doc.forEach((partNode) => {
    if (partNode.type.name !== 'part') return;

    partNode.forEach((child) => {
      if (child.type.name === 'label') {
        lines.push(`# ${child.textContent}`);
        lines.push('');
      } else if (child.type.name === 'line') {
        lines.push(child.textContent);
      }
    });

    lines.push('');
  });

  return lines.join('\n').trim();
}

/**
 * Get all part IDs in document order.
 */
export function getPartIds(doc: ProseMirrorNode): string[] {
  const ids: string[] = [];

  doc.forEach((partNode) => {
    if (partNode.type.name === 'part' && partNode.attrs.id) {
      ids.push(partNode.attrs.id);
    }
  });

  return ids;
}

/**
 * Find a part node by ID.
 */
export function findPartById(
  doc: ProseMirrorNode,
  partId: string
): { node: ProseMirrorNode; pos: number } | null {
  let result: { node: ProseMirrorNode; pos: number } | null = null;
  let pos = 0;

  doc.forEach((partNode, offset) => {
    if (partNode.type.name === 'part' && partNode.attrs.id === partId) {
      result = { node: partNode, pos: offset + 1 }; // +1 for doc start
    }
  });

  return result;
}
