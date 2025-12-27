'use client';

import { Song, SectionType } from '@/types';
import { StatusBadge } from '@/components/StatusBadge';
import { ChordSheetView } from './ChordSheetView';

interface LivePreviewPanelProps {
  song: Song;
  selectedSectionId: string | null;
  onSectionClick?: (sectionId: string) => void;
  onPrint?: () => void;
  /** Enable editing in preview */
  editable?: boolean;
  /** Show chord lines above lyrics (default: true) */
  showChords?: boolean;
  /** Callback to toggle chord visibility */
  onToggleChords?: () => void;
  onAddChord?: (sectionId: string, lineId: string, chord: string, position: number) => void;
  onRemoveChord?: (sectionId: string, lineId: string, position: number) => void;
  /** Line editing callbacks */
  onUpdateLine?: (sectionId: string, lineId: string, text: string) => void;
  onAddLineAfter?: (sectionId: string, afterLineId: string, text: string) => Promise<string | undefined>;
  onDeleteLine?: (sectionId: string, lineId: string) => void;
  /** Merge line with previous */
  onMergeWithPrevious?: (sectionId: string, lineId: string, lineIndex: number, currentText: string) => Promise<{ focusLineId: string; cursorPosition: number } | undefined>;
  /** Section callbacks */
  onAddSectionAfter?: (sectionId: string) => Promise<string | undefined>;
  onDeleteSection?: (sectionId: string) => void;
  onUpdateSection?: (sectionId: string, type: SectionType) => void;
  onReorderSections?: (sectionIds: string[]) => void;
  onAddSection?: () => void;
  /** Version management callbacks */
  onDuplicateVersion?: (sectionId: string, versionId: string) => void;
  onSwitchVersion?: (sectionId: string, versionId: string) => void;
  /** Audio upload callback */
  onUploadAudio?: (sectionId: string, versionId: string, file: File) => void;
  isUploadingAudio?: boolean;
  /** Focus control for new lines */
  focusLineId?: string | null;
  focusCursorPosition?: number;
  onFocusHandled?: () => void;
}

export function LivePreviewPanel({
  song,
  selectedSectionId,
  onSectionClick,
  onPrint,
  editable = false,
  showChords = true,
  onToggleChords,
  onAddChord,
  onRemoveChord,
  onUpdateLine,
  onAddLineAfter,
  onDeleteLine,
  onMergeWithPrevious,
  onAddSectionAfter,
  onDeleteSection,
  onUpdateSection,
  onReorderSections,
  onAddSection,
  onDuplicateVersion,
  onSwitchVersion,
  onUploadAudio,
  isUploadingAudio,
  focusLineId,
  focusCursorPosition,
  onFocusHandled,
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
          <div className="flex items-center gap-2">
            <StatusBadge status={song.status} />
            {/* Add Section button */}
            {editable && (onAddSection || onAddSectionAfter) && (
              <button
                onClick={() => {
                  if (selectedSectionId && onAddSectionAfter) {
                    onAddSectionAfter(selectedSectionId);
                  } else if (onAddSection) {
                    onAddSection();
                  }
                }}
                className="
                  p-2 text-gray-500 dark:text-gray-400
                  hover:text-indigo-600 dark:hover:text-indigo-400
                  hover:bg-indigo-50 dark:hover:bg-indigo-900/30
                  rounded-lg transition-colors
                "
                title={selectedSectionId ? 'Add section below selected' : 'Add section'}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            )}
            {onToggleChords && (
              <button
                onClick={onToggleChords}
                className={`
                  p-2 rounded-lg transition-colors
                  ${showChords
                    ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }
                `}
                title={showChords ? 'Hide chords' : 'Show chords'}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
              </button>
            )}
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
          showChords={showChords}
          onAddChord={onAddChord}
          onRemoveChord={onRemoveChord}
          onUpdateLine={onUpdateLine}
          onAddLineAfter={onAddLineAfter}
          onDeleteLine={onDeleteLine}
          onMergeWithPrevious={onMergeWithPrevious}
          onAddSectionAfter={onAddSectionAfter}
          onDeleteSection={onDeleteSection}
          onUpdateSection={onUpdateSection}
          onReorderSections={onReorderSections}
          onAddSection={onAddSection}
          onDuplicateVersion={onDuplicateVersion}
          onSwitchVersion={onSwitchVersion}
          onUploadAudio={onUploadAudio}
          isUploadingAudio={isUploadingAudio}
          focusLineId={focusLineId}
          focusCursorPosition={focusCursorPosition}
          onFocusHandled={onFocusHandled}
        />
      </div>
    </div>
  );
}
