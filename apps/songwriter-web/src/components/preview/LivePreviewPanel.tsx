'use client';

import { Song } from '@/types';
import { StatusBadge } from '@/components/StatusBadge';
import { ChordSheetView } from './ChordSheetView';

interface LivePreviewPanelProps {
  song: Song;
  selectedSectionId: string | null;
  onSectionClick?: (sectionId: string) => void;
  onPrint?: () => void;
  /** Enable chord editing in preview */
  editable?: boolean;
  onAddChord?: (sectionId: string, lineId: string, chord: string, position: number) => void;
  onRemoveChord?: (sectionId: string, lineId: string, position: number) => void;
}

export function LivePreviewPanel({
  song,
  selectedSectionId,
  onSectionClick,
  onPrint,
  editable = false,
  onAddChord,
  onRemoveChord,
}: LivePreviewPanelProps) {
  const handlePrint = () => {
    if (onPrint) {
      onPrint();
    } else {
      window.print();
    }
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 min-h-0">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {song.title}
            </h1>
            <div className="flex items-center gap-3 mt-2 text-sm text-gray-500 dark:text-gray-400">
              {song.key && (
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                  Key of {song.key}
                </span>
              )}
              {song.tempo && (
                <span className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {song.tempo} BPM
                </span>
              )}
              {song.time_signature && song.time_signature !== '4/4' && (
                <span>{song.time_signature}</span>
              )}
              {song.feel && (
                <span className="italic">{song.feel}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={song.status} />
            <button
              onClick={handlePrint}
              className="
                p-2 text-gray-500 dark:text-gray-400
                hover:text-gray-700 dark:hover:text-gray-200
                hover:bg-gray-100 dark:hover:bg-gray-800
                rounded-lg transition-colors
              "
              title="Print chord sheet"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Chord Sheet Content */}
      <div className="flex-1 overflow-hidden min-h-0">
        <ChordSheetView
          song={song}
          selectedSectionId={selectedSectionId}
          onSectionClick={onSectionClick}
          editable={editable}
          onAddChord={onAddChord}
          onRemoveChord={onRemoveChord}
        />
      </div>
    </div>
  );
}
