/**
 * Document Parser
 *
 * Parses plain text from CodeMirror back into structured song format.
 * Recognizes: # section headers, > chord lines, // annotations
 */

import { SectionType, LineType } from '@/types/song';
import { ChordAnnotation } from './chordAnnotations';

export interface ParsedLine {
  text: string;
  lineType: LineType;
  chords: { chord: string; position: number }[];
}

export interface ParsedSection {
  type: SectionType;
  number?: number;
  lines: ParsedLine[];
}

export interface ParsedDocument {
  sections: ParsedSection[];
  rawText: string;
}

/**
 * Parse a section header to extract type and number.
 * Examples: "# Verse 1" -> { type: VERSE, number: 1 }
 *           "# Chorus" -> { type: CHORUS, number: undefined }
 */
function parseSectionHeader(text: string): { type: SectionType; number?: number } {
  // Remove the "# " prefix
  const content = text.replace(/^#\s*/, '').trim();

  // Try to match type and optional number
  const match = content.match(/^(.+?)(?:\s+(\d+))?$/i);
  if (!match) {
    return { type: SectionType.OTHER };
  }

  const typeName = match[1].toLowerCase().replace(/\s+/g, '_');
  const number = match[2] ? parseInt(match[2], 10) : undefined;

  // Map common names to section types
  const typeMap: Record<string, SectionType> = {
    'intro': SectionType.INTRO,
    'verse': SectionType.VERSE,
    'pre_chorus': SectionType.PRE_CHORUS,
    'pre-chorus': SectionType.PRE_CHORUS,
    'prechorus': SectionType.PRE_CHORUS,
    'chorus': SectionType.CHORUS,
    'post_chorus': SectionType.POST_CHORUS,
    'post-chorus': SectionType.POST_CHORUS,
    'postchorus': SectionType.POST_CHORUS,
    'bridge': SectionType.BRIDGE,
    'outro': SectionType.OUTRO,
    'instrumental': SectionType.INSTRUMENTAL,
    'solo': SectionType.SOLO,
    'breakdown': SectionType.BREAKDOWN,
    'brain_dump': SectionType.BRAIN_DUMP,
    'braindump': SectionType.BRAIN_DUMP,
    'brain dump': SectionType.BRAIN_DUMP,
    'other': SectionType.OTHER,
  };

  const sectionType = typeMap[typeName] || SectionType.OTHER;
  return { type: sectionType, number };
}

/**
 * Parse chord line content.
 * Example: "> Am G C F" -> just the chords text (for chord-type lines)
 */
function parseChordLine(text: string): string {
  return text.replace(/^>\s*/, '').trim();
}

/**
 * Parse annotation line content.
 * Example: "// This is a note" -> the note text
 */
function parseAnnotationLine(text: string): string {
  return text.replace(/^\/\/\s*/, '').trim();
}

/**
 * Determine line type from prefix (fallback when no state-based types provided).
 */
function getLineTypeFromPrefix(line: string): LineType {
  if (line.startsWith('> ') || line === '>') {
    return LineType.CHORD;
  }
  if (line.startsWith('// ') || line === '//') {
    return LineType.ANNOTATION;
  }
  return LineType.LYRIC;
}

/**
 * Parse the document text into structured format.
 *
 * @param text - The raw document text
 * @param chords - Chord annotations from the editor state
 * @param lineTypes - Optional map of line numbers (1-indexed) to line types from editor state
 */
export function parseDocument(
  text: string,
  chords: ChordAnnotation[] = [],
  lineTypes?: Map<number, LineType>
): ParsedDocument {
  const lines = text.split('\n');
  const sections: ParsedSection[] = [];
  let currentSection: ParsedSection | null = null;
  let lineIndex = 0;

  // Group chords by line number for quick lookup
  const chordsByLine = new Map<number, ChordAnnotation[]>();
  for (const chord of chords) {
    if (!chordsByLine.has(chord.line)) {
      chordsByLine.set(chord.line, []);
    }
    chordsByLine.get(chord.line)!.push(chord);
  }

  for (const line of lines) {
    const trimmedLine = line.trim();
    const lineNumber = lineIndex + 1; // Convert to 1-indexed for lineTypes map

    // Skip empty lines
    if (!trimmedLine) {
      lineIndex++;
      continue;
    }

    // Get line type from state or fall back to prefix detection
    const lineType = lineTypes?.get(lineNumber) ?? getLineTypeFromPrefix(trimmedLine);

    // Check for section header (from state or prefix)
    if (lineType === LineType.SECTION_HEADER || trimmedLine.startsWith('# ')) {
      // Save previous section if exists
      if (currentSection) {
        sections.push(currentSection);
      }

      // Start new section - parse header text (might have # prefix or not)
      const headerText = trimmedLine.startsWith('# ') ? trimmedLine : `# ${trimmedLine}`;
      const { type, number } = parseSectionHeader(headerText);
      currentSection = {
        type,
        number,
        lines: [],
      };
      lineIndex++;
      continue;
    }

    // If no section yet, create a default one
    if (!currentSection) {
      currentSection = {
        type: SectionType.VERSE,
        number: 1,
        lines: [],
      };
    }

    // Get line content (remove prefix if present, for backwards compat)
    let lineText = trimmedLine;
    if (trimmedLine.startsWith('> ') || trimmedLine === '>') {
      lineText = parseChordLine(trimmedLine);
    } else if (trimmedLine.startsWith('// ') || trimmedLine === '//') {
      lineText = parseAnnotationLine(trimmedLine);
    }

    // Get chords for this line
    const lineChords = chordsByLine.get(lineIndex) || [];
    const parsedChords = lineChords.map((c) => ({
      chord: c.chord,
      position: c.position,
    }));

    currentSection.lines.push({
      text: lineText,
      lineType,
      chords: parsedChords,
    });

    lineIndex++;
  }

  // Don't forget the last section
  if (currentSection) {
    sections.push(currentSection);
  }

  return {
    sections,
    rawText: text,
  };
}

/**
 * Convert parsed document to format suitable for API save.
 */
export function toApiFormat(doc: ParsedDocument): {
  sections: Array<{
    type: SectionType;
    number?: number;
    lines: Array<{
      text: string;
      line_type: LineType;
      chords: Array<{ chord: string; position: number }>;
    }>;
  }>;
  raw_text: string;
} {
  return {
    sections: doc.sections.map((section) => ({
      type: section.type,
      number: section.number,
      lines: section.lines.map((line) => ({
        text: line.text,
        line_type: line.lineType,
        chords: line.chords,
      })),
    })),
    raw_text: doc.rawText,
  };
}
