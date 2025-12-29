/**
 * Canvas Editor Types
 *
 * Types for the canvas-based song editor that treats songs as flat lists of lines.
 */

import { LineType } from '@/types/song';

export interface CanvasLine {
  id: string;
  lineType: LineType;
  text: string;
  order: number;
}

export interface LineTypeConfig {
  type: LineType;
  prefix: string;
  icon: string;
  label: string;
  placeholder: string;
  className?: string;
}

export const LINE_TYPE_CONFIGS: Record<LineType, LineTypeConfig> = {
  [LineType.SECTION_HEADER]: {
    type: LineType.SECTION_HEADER,
    prefix: '#',
    icon: '§',
    label: 'Section Header',
    placeholder: 'Verse 1, Chorus, Bridge...',
    className: 'font-bold text-lg',
  },
  [LineType.LYRIC]: {
    type: LineType.LYRIC,
    prefix: '',
    icon: '¶',
    label: 'Lyric',
    placeholder: 'Write your lyrics...',
  },
  [LineType.CHORD]: {
    type: LineType.CHORD,
    prefix: '>',
    icon: '♪',
    label: 'Chord',
    placeholder: 'Am G C F...',
    className: 'font-mono text-blue-600 dark:text-blue-400',
  },
  [LineType.ANNOTATION]: {
    type: LineType.ANNOTATION,
    prefix: '//',
    icon: '✎',
    label: 'Annotation',
    placeholder: 'Add a note...',
    className: 'italic text-gray-500 dark:text-gray-400',
  },
};

/**
 * Detect line type from prefix and return the cleaned text.
 * Returns null if no prefix detected (stays as current type).
 */
export function detectPrefixAndTransform(
  text: string
): { lineType: LineType; cleanedText: string } | null {
  // Check for section header: "# "
  if (text.startsWith('# ')) {
    return {
      lineType: LineType.SECTION_HEADER,
      cleanedText: text.slice(2),
    };
  }

  // Check for chord: "> "
  if (text.startsWith('> ')) {
    return {
      lineType: LineType.CHORD,
      cleanedText: text.slice(2),
    };
  }

  // Check for annotation: "// "
  if (text.startsWith('// ')) {
    return {
      lineType: LineType.ANNOTATION,
      cleanedText: text.slice(3),
    };
  }

  return null;
}

/**
 * Get the prefix to restore when reverting a line type.
 */
export function getPrefixForType(lineType: LineType): string {
  const config = LINE_TYPE_CONFIGS[lineType];
  return config.prefix ? `${config.prefix} ` : '';
}
