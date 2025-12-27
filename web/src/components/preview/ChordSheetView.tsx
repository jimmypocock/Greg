'use client';

import { useEffect, useRef, useState, useMemo } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { Song, Section, SectionType } from '@/types';
import { SectionBlock } from './SectionBlock';

interface ChordSheetViewProps {
  song: Song;
  selectedSectionId: string | null;
  onSectionClick?: (sectionId: string) => void;
  /** Enable editing */
  editable?: boolean;
  /** Show chord lines above lyrics (default: true) */
  showChords?: boolean;
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

export function ChordSheetView({
  song,
  selectedSectionId,
  onSectionClick,
  editable = false,
  showChords = true,
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
}: ChordSheetViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  // Local optimistic state for sections order (for smooth drag)
  const [localSections, setLocalSections] = useState<Section[]>(song.sections);

  // Sync local state with props when sections change from server
  const sectionsKey = useMemo(() => {
    return song.sections.map(s => s.id).join('|');
  }, [song.sections]);

  useEffect(() => {
    setLocalSections(song.sections);
  }, [sectionsKey, song.sections]);

  // Drag and drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = localSections.findIndex((s) => s.id === active.id);
      const newIndex = localSections.findIndex((s) => s.id === over.id);
      const newOrder = arrayMove(localSections, oldIndex, newIndex);

      // Optimistically update local state immediately
      setLocalSections(newOrder);

      // Then trigger the server update
      if (onReorderSections) {
        onReorderSections(newOrder.map((s) => s.id));
      }
    }
  };

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
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-xs mb-4">
          Start writing your song by adding a section, or let AI suggest a structure from your raw lyrics.
        </p>
        {editable && onAddSection && (
          <button
            onClick={onAddSection}
            className="
              px-6 py-3 text-sm font-medium
              text-white bg-indigo-600
              hover:bg-indigo-700
              rounded-lg transition-colors
            "
          >
            + Add First Section
          </button>
        )}
      </div>
    );
  }

  const isDraggable = editable && !!onReorderSections;

  return (
    <div
      ref={containerRef}
      className="h-full overflow-y-auto p-6 lg:p-8"
    >
      <div className="max-w-2xl mx-auto">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext
            items={localSections.map((s) => s.id)}
            strategy={verticalListSortingStrategy}
          >
            {localSections.map((section, index) => (
              <SectionBlock
                key={section.id}
                section={section}
                songId={song.id}
                isSelected={section.id === selectedSectionId}
                isFirst={index === 0}
                onClick={onSectionClick ? () => onSectionClick(section.id) : undefined}
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
                onDuplicateVersion={onDuplicateVersion}
                onSwitchVersion={onSwitchVersion}
                onUploadAudio={onUploadAudio}
                isUploadingAudio={isUploadingAudio}
                isDraggable={isDraggable}
                focusLineId={focusLineId}
                focusCursorPosition={focusCursorPosition}
                onFocusHandled={onFocusHandled}
              />
            ))}
          </SortableContext>
        </DndContext>
      </div>
    </div>
  );
}
