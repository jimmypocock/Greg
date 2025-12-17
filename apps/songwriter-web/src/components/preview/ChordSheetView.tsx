'use client';

import { useEffect, useRef } from 'react';
import { Song } from '@/types';
import { SectionBlock } from './SectionBlock';

interface ChordSheetViewProps {
  song: Song;
  selectedSectionId: string | null;
  onSectionClick?: (sectionId: string) => void;
  /** Enable chord editing */
  editable?: boolean;
  onAddChord?: (sectionId: string, lineId: string, chord: string, position: number) => void;
  onRemoveChord?: (sectionId: string, lineId: string, position: number) => void;
}

export function ChordSheetView({
  song,
  selectedSectionId,
  onSectionClick,
  editable = false,
  onAddChord,
  onRemoveChord,
}: ChordSheetViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Scroll to selected section
  useEffect(() => {
    if (selectedSectionId && containerRef.current) {
      const element = document.getElementById(`section-${selectedSectionId}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }, [selectedSectionId]);

  if (song.sections.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8">
        <div className="text-6xl mb-4 opacity-20">
          <svg className="w-24 h-24 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
          No sections yet
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs">
          Add sections using the toolbox on the left, or let AI suggest a structure from your raw lyrics.
        </p>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="h-full overflow-y-auto p-6 lg:p-8"
    >
      <div className="max-w-2xl mx-auto">
        {song.sections.map((section) => (
          <SectionBlock
            key={section.id}
            section={section}
            isSelected={section.id === selectedSectionId}
            onClick={onSectionClick ? () => onSectionClick(section.id) : undefined}
            editable={editable}
            onAddChord={onAddChord}
            onRemoveChord={onRemoveChord}
          />
        ))}
      </div>
    </div>
  );
}
