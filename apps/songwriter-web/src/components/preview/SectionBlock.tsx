'use client';

import { Section, SectionType, Line } from '@/types';

interface SectionBlockProps {
  section: Section;
  isSelected?: boolean;
  onClick?: () => void;
}

const sectionLabels: Record<SectionType, string> = {
  [SectionType.INTRO]: 'INTRO',
  [SectionType.VERSE]: 'VERSE',
  [SectionType.PRE_CHORUS]: 'PRE-CHORUS',
  [SectionType.CHORUS]: 'CHORUS',
  [SectionType.POST_CHORUS]: 'POST-CHORUS',
  [SectionType.BRIDGE]: 'BRIDGE',
  [SectionType.OUTRO]: 'OUTRO',
  [SectionType.INSTRUMENTAL]: 'INSTRUMENTAL',
  [SectionType.SOLO]: 'SOLO',
  [SectionType.BREAKDOWN]: 'BREAKDOWN',
  [SectionType.OTHER]: 'OTHER',
};

function renderChordLine(text: string, chords: { chord: string; position: number }[]): string {
  if (chords.length === 0) return '';

  const sortedChords = [...chords].sort((a, b) => a.position - b.position);
  const chordLine = Array(Math.max(text.length + 10, 1)).fill(' ');

  for (const { chord, position } of sortedChords) {
    for (let i = 0; i < chord.length; i++) {
      const pos = position + i;
      if (pos < chordLine.length) {
        chordLine[pos] = chord[i];
      } else {
        chordLine.push(chord[i]);
      }
    }
  }

  return chordLine.join('').trimEnd();
}

function LineDisplay({ line }: { line: Line }) {
  const chordLine = renderChordLine(line.text, line.chords);

  return (
    <div className="leading-relaxed">
      {chordLine && (
        <div className="text-indigo-600 dark:text-indigo-400 font-bold whitespace-pre">
          {chordLine}
        </div>
      )}
      <div className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
        {line.text || '\u00A0'}
      </div>
    </div>
  );
}

export function SectionBlock({ section, isSelected, onClick }: SectionBlockProps) {
  const label = sectionLabels[section.type] || section.type;
  const fullLabel = section.number ? `${label} ${section.number}` : label;

  return (
    <div
      id={`section-${section.id}`}
      onClick={onClick}
      className={`
        mb-6 scroll-mt-4
        ${onClick ? 'cursor-pointer' : ''}
        ${isSelected ? 'ring-2 ring-indigo-500 ring-offset-2 rounded-lg' : ''}
        transition-all duration-200
      `}
    >
      {/* Section Header */}
      <div className="mb-2">
        <span className="
          text-xs font-bold tracking-wider
          text-gray-500 dark:text-gray-400
          bg-gray-100 dark:bg-gray-800
          px-2 py-1 rounded
        ">
          [{fullLabel}]
        </span>
      </div>

      {/* Lines */}
      <div className="font-mono text-sm pl-1 space-y-1">
        {section.lines.length === 0 ? (
          <p className="text-gray-400 dark:text-gray-500 italic">
            (empty section)
          </p>
        ) : (
          section.lines.map((line) => (
            <LineDisplay key={line.id} line={line} />
          ))
        )}
      </div>
    </div>
  );
}
