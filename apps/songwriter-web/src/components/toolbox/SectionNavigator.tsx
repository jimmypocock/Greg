'use client';

import { useState, useEffect, useMemo, useRef } from 'react';
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
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Section, SectionType, Line, SectionVersionSummary } from '@/types';
import { useVersionAudioFiles, useDeleteAudio } from '@/lib/audioHooks';
import type { AudioFile } from '@/types/audio';

interface SectionNavigatorProps {
  sections: Section[];
  songId: string;
  selectedSectionId: string | null;
  onSelectSection: (sectionId: string | null) => void;
  onReorderSections: (sectionIds: string[]) => void;
  onReorderLines: (sectionId: string, lineIds: string[]) => void;
  onUpdateLine: (sectionId: string, lineId: string, text: string) => void;
  onAddLine: (sectionId: string) => void;
  onAddLineWithText: (sectionId: string, text: string) => void;
  onDeleteLine: (sectionId: string, lineId: string) => void;
  onDeleteSection: (sectionId: string) => void;
  onUpdateSection: (sectionId: string, type: SectionType) => void;
  onAddSection?: () => void;
  // Version props - selecting a version promotes it to main
  onDuplicateVersion?: (sectionId: string, versionId: string) => void;
  onSwitchVersion?: (sectionId: string, versionId: string) => void;
  // Audio upload for version
  onUploadVersionAudio?: (sectionId: string, versionId: string, file: File) => void;
  isUploadingAudio?: boolean;
  isMutating?: boolean;
}

const sectionLabels: Record<SectionType, string> = {
  [SectionType.INTRO]: 'Intro',
  [SectionType.VERSE]: 'Verse',
  [SectionType.PRE_CHORUS]: 'Pre-Chorus',
  [SectionType.CHORUS]: 'Chorus',
  [SectionType.POST_CHORUS]: 'Post-Chorus',
  [SectionType.BRIDGE]: 'Bridge',
  [SectionType.OUTRO]: 'Outro',
  [SectionType.INSTRUMENTAL]: 'Instrumental',
  [SectionType.SOLO]: 'Solo',
  [SectionType.BREAKDOWN]: 'Breakdown',
  [SectionType.OTHER]: 'Other',
};

const sectionColors: Record<SectionType, string> = {
  [SectionType.INTRO]: 'border-l-gray-400',
  [SectionType.VERSE]: 'border-l-blue-500',
  [SectionType.PRE_CHORUS]: 'border-l-purple-400',
  [SectionType.CHORUS]: 'border-l-indigo-500',
  [SectionType.POST_CHORUS]: 'border-l-purple-500',
  [SectionType.BRIDGE]: 'border-l-amber-500',
  [SectionType.OUTRO]: 'border-l-gray-500',
  [SectionType.INSTRUMENTAL]: 'border-l-teal-500',
  [SectionType.SOLO]: 'border-l-pink-500',
  [SectionType.BREAKDOWN]: 'border-l-red-500',
  [SectionType.OTHER]: 'border-l-gray-400',
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';

// Simple audio player for version audio files
function VersionAudioItem({ audioFile, songId }: { audioFile: AudioFile; songId: string }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const deleteAudio = useDeleteAudio(songId);
  const [showConfirm, setShowConfirm] = useState(false);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleDelete = async () => {
    await deleteAudio.mutateAsync(audioFile.id);
    setShowConfirm(false);
  };

  return (
    <div className="flex items-center gap-2 py-1.5 px-2 bg-gray-50 dark:bg-gray-750 rounded text-xs">
      <audio
        ref={audioRef}
        src={`${API_BASE_URL}/songs/${songId}/audio/${audioFile.id}/stream`}
        preload="metadata"
        onEnded={() => setIsPlaying(false)}
      />
      <button
        onClick={togglePlay}
        className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-200"
      >
        {isPlaying ? (
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
          </svg>
        ) : (
          <svg className="w-3 h-3 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>
      <span className="flex-1 truncate text-gray-600 dark:text-gray-300" title={audioFile.filename}>
        {audioFile.display_name || audioFile.filename}
      </span>
      {showConfirm ? (
        <div className="flex items-center gap-1">
          <button
            onClick={handleDelete}
            disabled={deleteAudio.isPending}
            className="px-1.5 py-0.5 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
          >
            {deleteAudio.isPending ? '...' : 'Delete'}
          </button>
          <button
            onClick={() => setShowConfirm(false)}
            className="px-1.5 py-0.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setShowConfirm(true)}
          className="p-1 text-gray-400 hover:text-red-500"
          title="Delete"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}

// Sortable Line Component
interface SortableLineProps {
  line: { id: string; text: string };
  isEditing: boolean;
  editText: string;
  onStartEdit: () => void;
  onEditChange: (text: string) => void;
  onSaveEdit: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onPasteMultiline: (lines: string[]) => void;
  onDelete: () => void;
  isMutating?: boolean;
}

function SortableLine({
  line,
  isEditing,
  editText,
  onStartEdit,
  onEditChange,
  onSaveEdit,
  onKeyDown,
  onPasteMultiline,
  onDelete,
  isMutating,
}: SortableLineProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: line.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`group flex items-start gap-1 ${isDragging ? 'opacity-50' : ''}`}
    >
      {isEditing ? (
        <input
          type="text"
          value={editText}
          onChange={(e) => onEditChange(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={onSaveEdit}
          onPaste={(e) => {
            const pastedText = e.clipboardData.getData('text');
            // Check if pasted text has multiple lines
            if (pastedText.includes('\n')) {
              e.preventDefault();
              const lines = pastedText.split('\n').map(l => l.trim()).filter(l => l);
              if (lines.length > 0) {
                onPasteMultiline(lines);
              }
            }
            // Single line paste is handled normally by the input
          }}
          autoFocus
          className="
            flex-1 px-2 py-1 text-xs font-mono
            bg-white dark:bg-gray-900
            border border-indigo-300 dark:border-indigo-600
            rounded
            focus:outline-none focus:ring-1 focus:ring-indigo-500
          "
        />
      ) : (
        <>
          {/* Line Drag Handle */}
          <div
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 p-1"
            onClick={(e) => e.stopPropagation()}
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
            </svg>
          </div>
          <div
            onClick={onStartEdit}
            className="
              flex-1 px-2 py-1 text-xs font-mono
              text-gray-700 dark:text-gray-300
              hover:bg-gray-50 dark:hover:bg-gray-750
              rounded cursor-text truncate
            "
            title={line.text || '(empty)'}
          >
            {line.text || <span className="text-gray-400 italic">(empty)</span>}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (!isMutating) {
                onDelete();
              }
            }}
            disabled={isMutating}
            className={`
              opacity-0 group-hover:opacity-100
              p-1 text-gray-400 hover:text-red-500
              transition-opacity cursor-pointer
              ${isMutating ? 'cursor-not-allowed opacity-50' : ''}
            `}
            title="Delete line"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </>
      )}
    </div>
  );
}

interface SortableSectionProps {
  section: Section;
  songId: string;
  lines: Line[]; // Optimistic lines state
  isExpanded: boolean;
  onToggle: () => void;
  onUpdateLine: (lineId: string, text: string) => void;
  onAddLine: () => void;
  onAddLineWithText: (text: string) => void;
  onDeleteLine: (lineId: string) => void;
  onDeleteSection: () => void;
  onUpdateSection: (type: SectionType) => void;
  onReorderLines: (lineIds: string[], newLines: Line[]) => void;
  onOptimisticLineUpdate: (lineId: string, text: string) => void;
  // Version props - selecting a version promotes it to main
  onDuplicateVersion?: () => void;
  onSwitchVersion?: (versionId: string) => void;
  // Audio upload for version
  onUploadAudio?: (file: File) => void;
  isUploadingAudio?: boolean;
  isMutating?: boolean;
}

function SortableSection({
  section,
  songId,
  lines,
  isExpanded,
  onToggle,
  onUpdateLine,
  onAddLine,
  onAddLineWithText,
  onDeleteLine,
  onDeleteSection,
  onUpdateSection,
  onReorderLines,
  onOptimisticLineUpdate,
  onDuplicateVersion,
  onSwitchVersion,
  onUploadAudio,
  isUploadingAudio,
  isMutating,
}: SortableSectionProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: section.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const [editingLineId, setEditingLineId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  const [isEditingType, setIsEditingType] = useState(false);
  const [isVersionDropdownOpen, setIsVersionDropdownOpen] = useState(false);
  const versionDropdownRef = useRef<HTMLDivElement>(null);

  // Get current (main) version info
  const versions = section.versions || [];
  const mainVersion = versions.find(v => v.is_main) || versions[0];
  const mainVersionNumber = mainVersion?.version_number || 1;
  const mainVersionId = mainVersion?.id;

  // Fetch audio files for this version (only when expanded)
  const { data: versionAudioData, isLoading: isLoadingAudio } = useVersionAudioFiles(
    songId,
    mainVersionId || ''
  );
  const versionAudioFiles = versionAudioData?.audio_files || [];

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (versionDropdownRef.current && !versionDropdownRef.current.contains(event.target as Node)) {
        setIsVersionDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Track if we should auto-edit the next new line
  const shouldEditNewLine = useRef(false);
  const prevLinesCount = useRef(lines.length);

  // Auto-edit new line when it's created via Shift+Enter
  useEffect(() => {
    if (shouldEditNewLine.current && lines.length > prevLinesCount.current) {
      // A new line was added - start editing it
      const newLine = lines[lines.length - 1];
      if (newLine) {
        setEditingLineId(newLine.id);
        setEditText(newLine.text);
      }
      shouldEditNewLine.current = false;
    }
    prevLinesCount.current = lines.length;
  }, [lines]);

  // Sensors for line drag and drop
  const lineSensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleLineDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = lines.findIndex((l) => l.id === active.id);
      const newIndex = lines.findIndex((l) => l.id === over.id);
      const newLines = arrayMove(lines, oldIndex, newIndex);
      onReorderLines(newLines.map((l) => l.id), newLines);
    }
  };

  const label = sectionLabels[section.type] || section.type;
  const fullLabel = section.number ? `${label} ${section.number}` : label;

  const handleStartEdit = (lineId: string, currentText: string) => {
    setEditingLineId(lineId);
    setEditText(currentText);
  };

  const handleSaveEdit = () => {
    if (editingLineId) {
      // Optimistically update local state immediately
      onOptimisticLineUpdate(editingLineId, editText);
      // Then trigger server update
      onUpdateLine(editingLineId, editText);
    }
    setEditingLineId(null);
    setEditText('');
  };

  const handlePasteMultiline = (lineId: string, pastedLines: string[]) => {
    if (pastedLines.length === 0) return;

    // Update the current line with the first pasted line
    const firstLine = pastedLines[0];
    onOptimisticLineUpdate(lineId, firstLine);
    onUpdateLine(lineId, firstLine);

    // Add new lines for the rest
    for (let i = 1; i < pastedLines.length; i++) {
      onAddLineWithText(pastedLines[i]);
    }

    // Close the editor
    setEditingLineId(null);
    setEditText('');
  };

  const handleSaveAndNewLine = () => {
    if (editingLineId) {
      // Optimistically update local state immediately
      onOptimisticLineUpdate(editingLineId, editText);
      // Then trigger server update
      onUpdateLine(editingLineId, editText);
      // Flag that we want to edit the new line when it appears
      shouldEditNewLine.current = true;
      // Add a new line
      onAddLine();
    }
    // Clear current edit state (useEffect will set new edit when line appears)
    setEditingLineId(null);
    setEditText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      handleSaveAndNewLine();
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      setEditingLineId(null);
      setEditText('');
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`
        border-l-4 ${sectionColors[section.type]}
        bg-white dark:bg-gray-800
        rounded-r-lg
        transition-all duration-150
        ${isDragging ? 'opacity-50 shadow-lg z-10' : ''}
      `}
    >
      {/* Section Header */}
      <div
        className="group/header flex items-center px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750"
        onClick={onToggle}
      >
        {/* Drag Handle */}
        <div
          {...attributes}
          {...listeners}
          className="mr-2 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600"
          onClick={(e) => e.stopPropagation()}
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
          </svg>
        </div>

        <div className="flex-1">
          {isEditingType ? (
            <select
              value={section.type}
              onChange={(e) => {
                onUpdateSection(e.target.value as SectionType);
                setIsEditingType(false);
              }}
              onBlur={() => setIsEditingType(false)}
              onClick={(e) => e.stopPropagation()}
              autoFocus
              className="
                text-sm font-medium
                bg-white dark:bg-gray-900
                border border-indigo-300 dark:border-indigo-600
                rounded px-2 py-0.5
                focus:outline-none focus:ring-1 focus:ring-indigo-500
                cursor-pointer
              "
            >
              {Object.entries(sectionLabels).map(([type, label]) => (
                <option key={type} value={type}>
                  {label}
                </option>
              ))}
            </select>
          ) : (
            <span
              className="text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-indigo-600 dark:hover:text-indigo-400 cursor-pointer"
              onClick={(e) => {
                e.stopPropagation();
                setIsEditingType(true);
              }}
              title="Click to change section type"
            >
              {fullLabel}
            </span>
          )}
          <span className="ml-2 text-xs text-gray-400">
            {lines.length} {lines.length === 1 ? 'line' : 'lines'}
          </span>
        </div>

        {/* Version Selector */}
        {versions.length > 0 && (
          <div className="relative mr-2" ref={versionDropdownRef}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsVersionDropdownOpen(!isVersionDropdownOpen);
              }}
              className="
                flex items-center gap-1 px-2 py-0.5
                text-xs font-medium
                rounded border
                transition-colors
                bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600
                hover:bg-gray-200 dark:hover:bg-gray-600
              "
              title="Switch version"
            >
              <span>v{mainVersionNumber}</span>
              {versions.length > 1 && (
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              )}
            </button>

            {/* Version Dropdown */}
            {isVersionDropdownOpen && (
              <div className="absolute right-0 top-full mt-1 z-20 min-w-40 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1">
                {/* Version List */}
                {versions.map((version) => (
                  <button
                    key={version.id}
                    className={`
                      w-full px-3 py-2 text-left flex items-center justify-between
                      ${version.is_main
                        ? 'bg-indigo-50 dark:bg-indigo-900/30'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-750'
                      }
                    `}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!version.is_main && onSwitchVersion) {
                        onSwitchVersion(version.id);
                      }
                      setIsVersionDropdownOpen(false);
                    }}
                    disabled={version.is_main}
                  >
                    <span className={`text-sm font-medium ${version.is_main ? 'text-indigo-700 dark:text-indigo-300' : 'text-gray-700 dark:text-gray-200'}`}>
                      v{version.version_number}
                    </span>
                    <span className="text-xs text-gray-400">
                      {version.line_count} {version.line_count === 1 ? 'line' : 'lines'}
                    </span>
                  </button>
                ))}

                {/* Divider and Duplicate Button */}
                {onDuplicateVersion && (
                  <>
                    <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDuplicateVersion();
                        setIsVersionDropdownOpen(false);
                      }}
                      disabled={isMutating}
                      className={`
                        w-full px-3 py-2 text-left text-sm
                        text-indigo-600 dark:text-indigo-400
                        hover:bg-indigo-50 dark:hover:bg-indigo-900/30
                        ${isMutating ? 'opacity-50 cursor-not-allowed' : ''}
                      `}
                    >
                      + Duplicate to new version
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Delete Section Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (!isMutating) {
              onDeleteSection();
            }
          }}
          disabled={isMutating}
          className={`
            opacity-0 group-hover/header:opacity-100
            p-1 mr-1 text-gray-400 hover:text-red-500
            transition-opacity cursor-pointer
            ${isMutating ? 'cursor-not-allowed opacity-50' : ''}
          `}
          title="Delete section"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>

        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Expanded Content - Line Editor with Drag & Drop */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-100 dark:border-gray-700">
          <div className="mt-2 space-y-1">
            {lines.length === 0 ? (
              <p className="text-xs text-gray-400 italic py-2">No lines yet</p>
            ) : (
              <DndContext
                sensors={lineSensors}
                collisionDetection={closestCenter}
                onDragEnd={handleLineDragEnd}
              >
                <SortableContext
                  items={lines.map((l) => l.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {lines.map((line) => (
                    <SortableLine
                      key={line.id}
                      line={line}
                      isEditing={editingLineId === line.id}
                      editText={editText}
                      onStartEdit={() => handleStartEdit(line.id, line.text)}
                      onEditChange={setEditText}
                      onSaveEdit={handleSaveEdit}
                      onKeyDown={handleKeyDown}
                      onPasteMultiline={(pastedLines) => handlePasteMultiline(line.id, pastedLines)}
                      onDelete={() => onDeleteLine(line.id)}
                      isMutating={isMutating}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            )}
          </div>
          <div className="flex gap-2 mt-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (!isMutating) {
                  onAddLine();
                }
              }}
              disabled={isMutating}
              className={`
                flex-1 py-1.5 text-xs
                text-indigo-600 dark:text-indigo-400
                hover:bg-indigo-50 dark:hover:bg-indigo-900/20
                rounded transition-colors
                ${isMutating ? 'cursor-not-allowed opacity-50' : ''}
              `}
            >
              {isMutating ? 'Working...' : '+ Add Line'}
            </button>

            {/* Audio upload for this version */}
            {onUploadAudio && (
              <label
                className={`
                  flex items-center gap-1 px-2 py-1.5 text-xs
                  text-gray-500 dark:text-gray-400
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  rounded cursor-pointer transition-colors
                  ${isUploadingAudio ? 'opacity-50 cursor-not-allowed' : ''}
                `}
                title="Upload audio snippet for this version"
              >
                <input
                  type="file"
                  accept="audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/x-m4a,audio/mp4"
                  className="hidden"
                  disabled={isUploadingAudio}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      onUploadAudio(file);
                      e.target.value = '';
                    }
                  }}
                  onClick={(e) => e.stopPropagation()}
                />
                {isUploadingAudio ? (
                  <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                  </svg>
                )}
                <span>Audio</span>
              </label>
            )}
          </div>

          {/* Version audio files */}
          {versionAudioFiles.length > 0 && (
            <div className="mt-3 pt-2 border-t border-gray-100 dark:border-gray-700 space-y-1">
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Audio snippets:</div>
              {versionAudioFiles.map((audioFile) => (
                <VersionAudioItem key={audioFile.id} audioFile={audioFile} songId={songId} />
              ))}
            </div>
          )}
          {isLoadingAudio && isExpanded && (
            <div className="mt-2 text-xs text-gray-400 animate-pulse">Loading audio...</div>
          )}
        </div>
      )}
    </div>
  );
}

export function SectionNavigator({
  sections,
  songId,
  selectedSectionId,
  onSelectSection,
  onReorderSections,
  onReorderLines,
  onUpdateLine,
  onAddLine,
  onAddLineWithText,
  onDeleteLine,
  onDeleteSection,
  onUpdateSection,
  onAddSection,
  onDuplicateVersion,
  onSwitchVersion,
  onUploadVersionAudio,
  isUploadingAudio,
  isMutating,
}: SectionNavigatorProps) {
  // Local optimistic state for sections order
  const [localSections, setLocalSections] = useState<Section[]>(sections);

  // Local optimistic state for lines order per section
  const [localLinesMap, setLocalLinesMap] = useState<Record<string, Line[]>>(() => {
    const map: Record<string, Line[]> = {};
    sections.forEach(s => { map[s.id] = s.lines; });
    return map;
  });

  // Sync local state with props when sections change from server
  // Use a key based on section IDs, line IDs, and line text to detect real changes
  const sectionsKey = useMemo(() => {
    return sections.map(s => `${s.id}:${s.lines.map(l => `${l.id}=${l.text}`).join(',')}`).join('|');
  }, [sections]);

  useEffect(() => {
    setLocalSections(sections);
    const map: Record<string, Line[]> = {};
    sections.forEach(s => { map[s.id] = s.lines; });
    setLocalLinesMap(map);
  }, [sectionsKey]);

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
      onReorderSections(newOrder.map((s) => s.id));
    }
  };

  const handleReorderLines = (sectionId: string, lineIds: string[], newLines: Line[]) => {
    // Optimistically update local state immediately
    setLocalLinesMap(prev => ({
      ...prev,
      [sectionId]: newLines,
    }));

    // Then trigger the server update
    onReorderLines(sectionId, lineIds);
  };

  const handleOptimisticLineUpdate = (sectionId: string, lineId: string, text: string) => {
    // Optimistically update line text in local state
    setLocalLinesMap(prev => {
      const sectionLines = prev[sectionId] || [];
      return {
        ...prev,
        [sectionId]: sectionLines.map(line =>
          line.id === lineId ? { ...line, text } : line
        ),
      };
    });
  };

  if (sections.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
          No sections yet
        </p>
        {onAddSection && (
          <button
            onClick={onAddSection}
            className="
              px-4 py-2 text-sm font-medium
              bg-indigo-600 text-white
              rounded-lg hover:bg-indigo-700
              transition-colors
            "
          >
            + Add Section
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={localSections.map((s) => s.id)}
          strategy={verticalListSortingStrategy}
        >
          {localSections.map((section) => {
            const mainVersionId = section.main_version_id || section.versions?.[0]?.id;
            return (
              <SortableSection
                key={section.id}
                section={section}
                songId={songId}
                lines={localLinesMap[section.id] || section.lines}
                isExpanded={section.id === selectedSectionId}
                onToggle={() => onSelectSection(section.id === selectedSectionId ? null : section.id)}
                onUpdateLine={(lineId, text) => onUpdateLine(section.id, lineId, text)}
                onAddLine={() => onAddLine(section.id)}
                onAddLineWithText={(text) => onAddLineWithText(section.id, text)}
                onDeleteLine={(lineId) => onDeleteLine(section.id, lineId)}
                onDeleteSection={() => onDeleteSection(section.id)}
                onUpdateSection={(type) => onUpdateSection(section.id, type)}
                onReorderLines={(lineIds, newLines) => handleReorderLines(section.id, lineIds, newLines)}
                onOptimisticLineUpdate={(lineId, text) => handleOptimisticLineUpdate(section.id, lineId, text)}
                onDuplicateVersion={onDuplicateVersion && mainVersionId ? () => onDuplicateVersion(section.id, mainVersionId) : undefined}
                onSwitchVersion={onSwitchVersion ? (versionId) => onSwitchVersion(section.id, versionId) : undefined}
                onUploadAudio={onUploadVersionAudio && mainVersionId ? (file) => onUploadVersionAudio(section.id, mainVersionId, file) : undefined}
                isUploadingAudio={isUploadingAudio}
                isMutating={isMutating}
              />
            );
          })}
        </SortableContext>
      </DndContext>

      {onAddSection && (
        <button
          onClick={onAddSection}
          className="
            w-full py-2 text-sm
            text-indigo-600 dark:text-indigo-400
            hover:bg-indigo-50 dark:hover:bg-indigo-900/20
            rounded-lg transition-colors
          "
        >
          + Add Section
        </button>
      )}
    </div>
  );
}
