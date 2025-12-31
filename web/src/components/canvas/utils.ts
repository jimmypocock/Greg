/**
 * ProseMirror Utilities
 *
 * Conversion between ProseMirror documents and API data structures.
 */

import { Node as ProseMirrorNode } from 'prosemirror-model';
import { LineType, CanvasLine } from '@/types/song';

/**
 * Line data extracted from ProseMirror document.
 */
export interface LineData {
  id: string;
  text: string;
  lineType: LineType;
}

/**
 * Extract line data from a ProseMirror document.
 */
export function docToLines(doc: ProseMirrorNode): LineData[] {
  const lines: LineData[] = [];

  doc.forEach((lineNode) => {
    if (lineNode.type.name !== 'line') return;

    let text = lineNode.textContent;
    const lineType = lineNode.attrs.lineType as LineType;

    // Remove prefix from text for storage (prefix is just for editing)
    if (lineType === LineType.CHORD && text.startsWith('> ')) {
      text = text.slice(2);
    } else if (lineType === LineType.ANNOTATION && text.startsWith('// ')) {
      text = text.slice(3);
    } else if (lineType === LineType.SECTION_HEADER && text.startsWith('# ')) {
      text = text.slice(2);
    }

    lines.push({
      id: lineNode.attrs.id,
      text,
      lineType,
    });
  });

  return lines;
}

/**
 * Convert ProseMirror document to canvas lines format.
 */
export function docToCanvasLines(doc: ProseMirrorNode): CanvasLine[] {
  const lines = docToLines(doc);

  return lines.map((line) => ({
    id: line.id,
    text: line.text,
    line_type: line.lineType,
    chords: [], // Chords handled separately
  }));
}

/**
 * Get raw text content from document (for search/export).
 */
export function docToText(doc: ProseMirrorNode): string {
  const lines: string[] = [];

  doc.forEach((lineNode) => {
    if (lineNode.type.name !== 'line') return;
    lines.push(lineNode.textContent);
  });

  return lines.join('\n').trim();
}

/**
 * Get all line IDs in document order.
 */
export function getLineIds(doc: ProseMirrorNode): string[] {
  const ids: string[] = [];

  doc.forEach((lineNode) => {
    if (lineNode.type.name === 'line' && lineNode.attrs.id) {
      ids.push(lineNode.attrs.id);
    }
  });

  return ids;
}

/**
 * Find a line node by ID.
 */
export function findLineById(
  doc: ProseMirrorNode,
  lineId: string
): { node: ProseMirrorNode; pos: number } | null {
  let result: { node: ProseMirrorNode; pos: number } | null = null;

  doc.forEach((lineNode, offset) => {
    if (lineNode.type.name === 'line' && lineNode.attrs.id === lineId) {
      result = { node: lineNode, pos: offset + 1 }; // +1 for doc start
    }
  });

  return result;
}
