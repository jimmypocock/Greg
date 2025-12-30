/**
 * Canvas Editor Utilities
 *
 * Helper functions for converting between song structures and editor format.
 */

import { Song, LineType, SectionVersionSummary } from '@/types/song';
import { ChordAnnotation } from './chordAnnotations';

// Info about which section a line belongs to
export interface SectionLineInfo {
  sectionId: string;
  sectionIndex: number;
  mainVersionId: string | null;
  versions: SectionVersionSummary[];
}

// Result of converting song to text
export interface SongToTextResult {
  text: string;
  chords: ChordAnnotation[];
  lineTypes: Map<number, LineType>;
  sectionMap: Map<number, SectionLineInfo>;
}

/**
 * Convert song structure to plain text (no prefixes).
 * Returns text, chord annotations, initial line types, and section mapping.
 */
export function songToTextAndChords(song: Song): SongToTextResult {
  const lines: string[] = [];
  const chords: ChordAnnotation[] = [];
  const lineTypes = new Map<number, LineType>();
  const sectionMap = new Map<number, SectionLineInfo>();
  let lineNumber = 1; // CodeMirror lines are 1-indexed

  for (let sectionIndex = 0; sectionIndex < song.sections.length; sectionIndex++) {
    const section = song.sections[sectionIndex];
    const sectionInfo: SectionLineInfo = {
      sectionId: section.id,
      sectionIndex,
      mainVersionId: section.main_version_id,
      versions: section.versions || [],
    };

    // Section header (just the name, no prefix)
    const typeName = section.type.charAt(0).toUpperCase() + section.type.slice(1).replace('_', ' ');
    const headerText =
      section.number && section.number > 0 ? `${typeName} ${section.number}` : typeName;
    lines.push(headerText);
    lineTypes.set(lineNumber, LineType.SECTION_HEADER);
    sectionMap.set(lineNumber, sectionInfo);
    lineNumber++;

    // Section lines
    for (const line of section.lines) {
      lines.push(line.text);
      lineTypes.set(lineNumber, line.line_type || LineType.LYRIC);
      sectionMap.set(lineNumber, sectionInfo);

      // Extract chord placements from this line
      if (line.chords && line.chords.length > 0) {
        for (const placement of line.chords) {
          chords.push({
            line: lineNumber - 1, // 0-indexed for chord annotations
            position: placement.position,
            chord: placement.chord,
          });
        }
      }

      lineNumber++;
    }

    // Empty line between sections
    lines.push('');
    lineTypes.set(lineNumber, LineType.LYRIC);
    // Don't map empty lines to sections
    lineNumber++;
  }

  // If no sections, just return empty or raw input
  if (lines.length === 0) {
    return {
      text: song.raw_input || '',
      chords: [],
      lineTypes: new Map(),
      sectionMap: new Map(),
    };
  }

  return {
    text: lines.join('\n').trim(),
    chords,
    lineTypes,
    sectionMap,
  };
}
