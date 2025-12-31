/**
 * Constants for the Canvas editor
 */

import { LineType } from '@/types/song';

// Line type cycle order (for gutter click cycling)
export const LINE_TYPE_CYCLE: LineType[] = [
  LineType.LYRIC,
  LineType.SECTION_HEADER,
  LineType.CHORD,
  LineType.ANNOTATION,
];

// Gutter icons for each line type
export const LINE_TYPE_ICONS: Record<LineType, string> = {
  [LineType.LYRIC]: '',
  [LineType.SECTION_HEADER]: '#',
  [LineType.CHORD]: '>',
  [LineType.ANNOTATION]: '//',
};

// Drag handle icon
export const DRAG_ICON = '⋮⋮';
