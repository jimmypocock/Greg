'use client';

import { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Section, SectionType, Line, ChordPlacement, SectionVersionSummary } from '@/types';
import { sectionLabels } from '@/lib/constants';
import { ChordEditor } from './ChordEditor';
import { LexicalLineEditor } from '@/components/editor/LexicalLineEditor';
import { VersionAudioItem, AudioUploadButton } from './VersionAudioPlayer';
import { useAudioFiles } from '@/hooks/queries/audio';
import type { AudioFile } from '@/types/audio';

interface SectionBlockProps {
  section: Section;
  songId: string;
  isSelected?: boolean;
  isFirst?: boolean;
  onClick?: () => void;
  /** Enable editing mode */
  editable?: boolean;
  /** Show chord lines above lyrics (default: true) */
  showChords?: boolean;
  /** Called when a new chord is added */
  onAddChord?: (sectionId: string, lineId: string, chord: string, position: number) => void;
  /** Called when a chord is removed */
  onRemoveChord?: (sectionId: string, lineId: string, position: number) => void;
  /** Called when a line's text is updated */
  onUpdateLine?: (sectionId: string, lineId: string, text: string) => void;
  /** Called when a new line should be added after the specified line */
  onAddLineAfter?: (sectionId: string, afterLineId: string, text: string) => Promise<string | undefined>;
  /** Called when an empty line should be deleted */
  onDeleteLine?: (sectionId: string, lineId: string) => void;
  /** Called when merging current line with previous (backspace at start) */
  onMergeWithPrevious?: (sectionId: string, lineId: string, lineIndex: number, currentText: string) => Promise<{ focusLineId: string; cursorPosition: number } | undefined>;
  /** Called when creating a new section below */
  onAddSectionAfter?: (sectionId: string) => Promise<string | undefined>;
  /** Called when deleting a section */
  onDeleteSection?: (sectionId: string) => void;
  /** Called when updating section type */
  onUpdateSection?: (sectionId: string, type: SectionType) => void;
  /** ID of the line that should receive focus (for new line handling) */
  focusLineId?: string | null;
  /** Cursor position within the focused line */
  focusCursorPosition?: number;
  /** Called when focus has been handled */
  onFocusHandled?: () => void;
  /** Version management callbacks */
  onDuplicateVersion?: (sectionId: string, versionId: string) => void;
  onSwitchVersion?: (sectionId: string, versionId: string) => void;
  /** Audio upload callback */
  onUploadAudio?: (sectionId: string, versionId: string, file: File) => void;
  isUploadingAudio?: boolean;
  /** Whether drag-and-drop is enabled */
  isDraggable?: boolean;
}

/**
 * Hook to measure monospace character width accurately.
 * Creates a hidden element to measure the width of a single character.
 */
function useCharWidth(containerRef: React.RefObject<HTMLDivElement | null>): number {
  const [charWidth, setCharWidth] = useState(8); // Default fallback

  useEffect(() => {
    if (!containerRef.current) return;

    // Create a hidden measuring element with the same font styles
    const measureEl = document.createElement('span');
    measureEl.style.position = 'absolute';
    measureEl.style.visibility = 'hidden';
    measureEl.style.whiteSpace = 'pre';
    measureEl.style.font = 'inherit';
    measureEl.textContent = '0'; // Use '0' as reference character for monospace

    containerRef.current.appendChild(measureEl);
    const width = measureEl.getBoundingClientRect().width;
    containerRef.current.removeChild(measureEl);

    if (width > 0) {
      setCharWidth(width);
    }
  }, [containerRef]);

  return charWidth;
}

// Helper to get uppercase section label for display
function getSectionLabelUppercase(type: SectionType): string {
  return (sectionLabels[type] || type).toUpperCase();
}

function renderChordLine(text: string, chords: ChordPlacement[]): string {
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

interface EditableLineDisplayProps {
  line: Line;
  sectionId: string;
  lineIndex: number;
  isFirstLine: boolean;
  isLastLine: boolean;
  isOnlyLine: boolean;
  isSectionEmpty: boolean;
  isFirstSection: boolean;
  showChords?: boolean;
  onAddChord: (sectionId: string, lineId: string, chord: string, position: number) => void;
  onRemoveChord: (sectionId: string, lineId: string, position: number) => void;
  onUpdateLine: (sectionId: string, lineId: string, text: string) => void;
  onAddLineAfter: (sectionId: string, afterLineId: string, text: string) => Promise<string | undefined>;
  onDeleteLine: (sectionId: string, lineId: string) => void;
  onMergeWithPrevious?: (sectionId: string, lineId: string, lineIndex: number, currentText: string) => Promise<{ focusLineId: string; cursorPosition: number } | undefined>;
  onAddSectionAfter?: (sectionId: string) => Promise<string | undefined>;
  onDeleteSection?: (sectionId: string) => void;
  shouldFocus?: boolean;
  focusCursorPosition?: number;
  onFocusHandled?: () => void;
}

function EditableLineDisplay({
  line,
  sectionId,
  lineIndex,
  isFirstLine,
  isLastLine,
  isOnlyLine,
  isSectionEmpty,
  isFirstSection,
  showChords = true,
  onAddChord,
  onRemoveChord,
  onUpdateLine,
  onAddLineAfter,
  onDeleteLine,
  onMergeWithPrevious,
  onAddSectionAfter,
  onDeleteSection,
  shouldFocus,
  focusCursorPosition,
  onFocusHandled,
}: EditableLineDisplayProps) {
  const [chordEditorState, setChordEditorState] = useState<{
    position: number;
    anchorX: number;
    anchorY: number;
    existingChord?: ChordPlacement;
  } | null>(null);

  const [hoverPosition, setHoverPosition] = useState<number | null>(null);
  const [currentText, setCurrentText] = useState(line.text);

  const containerRef = useRef<HTMLDivElement>(null);
  const chordLineRef = useRef<HTMLDivElement>(null);

  // Get accurate character width for monospace font
  const charWidth = useCharWidth(containerRef);

  // Sync text when line prop changes externally
  useEffect(() => {
    setCurrentText(line.text);
  }, [line.text]);

  // Find chord at a given position
  const findChordAtPosition = useCallback((pos: number): ChordPlacement | undefined => {
    return line.chords.find(c => pos >= c.position && pos < c.position + c.chord.length);
  }, [line.chords]);

  // Calculate character position from click/mouse event on chord line
  const getCharPositionFromEvent = useCallback((e: React.MouseEvent<HTMLDivElement>): number => {
    if (!chordLineRef.current) return 0;

    const containerRect = chordLineRef.current.getBoundingClientRect();
    const clickX = e.clientX - containerRect.left;
    const position = Math.max(0, Math.floor(clickX / charWidth));

    return position;
  }, [charWidth]);

  // Handle click on chord line to add/edit chord
  const handleChordLineClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation();

    const position = getCharPositionFromEvent(e);
    const existingChord = findChordAtPosition(position);

    // Calculate anchor position for the popover
    const containerRect = chordLineRef.current?.getBoundingClientRect();
    const anchorX = containerRect ? containerRect.left + (position * charWidth) + (charWidth / 2) : e.clientX;
    const anchorY = containerRect?.top ?? e.clientY;

    setChordEditorState({
      position: existingChord ? existingChord.position : position,
      anchorX,
      anchorY,
      existingChord,
    });
    setHoverPosition(null);
  }, [getCharPositionFromEvent, findChordAtPosition, charWidth]);

  // Track mouse position for visual feedback on chord line
  const handleChordLineMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (chordEditorState) return;
    const position = getCharPositionFromEvent(e);
    setHoverPosition(position);
  }, [getCharPositionFromEvent, chordEditorState]);

  const handleChordLineMouseLeave = useCallback(() => {
    setHoverPosition(null);
  }, []);

  const handleSaveChord = useCallback(async (chord: string) => {
    if (chordEditorState) {
      await onAddChord(sectionId, line.id, chord, chordEditorState.position);
    }
    setChordEditorState(null);
  }, [chordEditorState, sectionId, line.id, onAddChord]);

  const handleDeleteChord = useCallback(async () => {
    if (chordEditorState?.existingChord) {
      await onRemoveChord(sectionId, line.id, chordEditorState.existingChord.position);
    }
    setChordEditorState(null);
  }, [chordEditorState, sectionId, line.id, onRemoveChord]);

  // Lexical editor callbacks
  const handleTextChange = useCallback((text: string) => {
    setCurrentText(text);
    // Debounce save to avoid too many updates
    // For now, we save on blur or Enter
  }, []);

  const handleEnter = useCallback(async (textBefore: string, textAfter: string) => {
    // Update current line with text before cursor
    if (textBefore !== line.text) {
      onUpdateLine(sectionId, line.id, textBefore);
    }
    // Create new line with text after cursor
    await onAddLineAfter(sectionId, line.id, textAfter);
  }, [sectionId, line.id, line.text, onUpdateLine, onAddLineAfter]);

  const handleShiftEnter = useCallback(async () => {
    if (onAddSectionAfter) {
      // Save current text first
      if (currentText !== line.text) {
        onUpdateLine(sectionId, line.id, currentText);
      }
      await onAddSectionAfter(sectionId);
    }
  }, [sectionId, line.id, line.text, currentText, onUpdateLine, onAddSectionAfter]);

  const handleBackspaceAtStart = useCallback(async (hasContent: boolean) => {
    if (!hasContent && isOnlyLine && isSectionEmpty) {
      // Empty line in empty section - delete section (if not the first section)
      if (onDeleteSection && !isFirstSection) {
        onDeleteSection(sectionId);
      }
    } else if (!hasContent && !isOnlyLine) {
      // Empty line (not the only one) - delete it
      onDeleteLine(sectionId, line.id);
    } else if (hasContent && !isFirstLine && onMergeWithPrevious) {
      // Line has content and there's a line above - merge with previous
      await onMergeWithPrevious(sectionId, line.id, lineIndex, currentText);
    }
  }, [sectionId, line.id, lineIndex, currentText, isFirstLine, isOnlyLine, isSectionEmpty, isFirstSection, onDeleteLine, onMergeWithPrevious, onDeleteSection]);

  const handleEscape = useCallback(() => {
    // Blur the editor - could also revert changes
  }, []);

  const handleBlur = useCallback(() => {
    // Save text on blur if changed
    if (currentText !== line.text) {
      onUpdateLine(sectionId, line.id, currentText);
    }
  }, [currentText, line.text, sectionId, line.id, onUpdateLine]);

  const chordLine = renderChordLine(currentText, line.chords);

  // Build the chord line with hover indicator
  const renderChordLineWithIndicator = () => {
    if (hoverPosition === null || chordEditorState) {
      return chordLine || '\u00A0';
    }

    const existingChord = findChordAtPosition(hoverPosition);
    if (existingChord) {
      return chordLine || '\u00A0';
    }

    const chars = (chordLine || '').split('');
    while (chars.length <= hoverPosition) {
      chars.push(' ');
    }

    if (chars[hoverPosition] === ' ' || chars[hoverPosition] === undefined) {
      chars[hoverPosition] = '│';
    }

    return chars.join('') || '\u00A0';
  };

  return (
    <div
      ref={containerRef}
      className="leading-normal group relative"
    >
      {/* Chord line - click to add/edit chords */}
      {showChords && (
        <div
          ref={chordLineRef}
          onClick={handleChordLineClick}
          onMouseMove={handleChordLineMouseMove}
          onMouseLeave={handleChordLineMouseLeave}
          className={`
            text-indigo-600 dark:text-indigo-400 font-bold whitespace-pre
            min-h-[1.25em] cursor-pointer
            hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded
            transition-colors
            ${!chordLine && hoverPosition === null ? 'opacity-0 group-hover:opacity-50' : ''}
          `}
          title="Click to add or edit chord"
        >
          {renderChordLineWithIndicator()}
        </div>
      )}

      {/* Lyric line - always editable with Lexical */}
      <LexicalLineEditor
        initialText={line.text}
        placeholder="..."
        onTextChange={handleTextChange}
        onEnter={handleEnter}
        onShiftEnter={handleShiftEnter}
        onBackspaceAtStart={handleBackspaceAtStart}
        onEscape={handleEscape}
        onBlur={handleBlur}
        shouldFocus={shouldFocus}
        focusCursorPosition={focusCursorPosition}
        onFocusHandled={onFocusHandled}
        className="min-h-[1.25em]"
      />

      {/* Chord editor popover */}
      {chordEditorState && (
        <ChordEditor
          initialChord={chordEditorState.existingChord?.chord || ''}
          anchorPosition={{ x: chordEditorState.anchorX, y: chordEditorState.anchorY }}
          onSave={handleSaveChord}
          onDelete={chordEditorState.existingChord ? handleDeleteChord : undefined}
          onClose={() => setChordEditorState(null)}
        />
      )}
    </div>
  );
}

function LineDisplay({ line, showChords = true }: { line: Line; showChords?: boolean }) {
  const chordLine = renderChordLine(line.text, line.chords);

  return (
    <div className="leading-relaxed">
      {showChords && chordLine && (
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

export function SectionBlock({
  section,
  songId,
  isSelected,
  isFirst = false,
  onClick,
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
  focusLineId,
  focusCursorPosition,
  onFocusHandled,
  onDuplicateVersion,
  onSwitchVersion,
  onUploadAudio,
  isUploadingAudio,
  isDraggable = false,
}: SectionBlockProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isVersionDropdownOpen, setIsVersionDropdownOpen] = useState(false);
  const [isAudioPanelOpen, setIsAudioPanelOpen] = useState(false);
  const [isEditingType, setIsEditingType] = useState(false);
  const versionDropdownRef = useRef<HTMLDivElement>(null);
  const audioPanelRef = useRef<HTMLDivElement>(null);

  const label = sectionLabels[section.type] || section.type;
  const fullLabel = section.number ? `${label} ${section.number}` : label;

  const canEdit = editable && onAddChord && onRemoveChord && onUpdateLine && onAddLineAfter && onDeleteLine;
  const isSectionEmpty = section.lines.length === 0 || (section.lines.length === 1 && section.lines[0].text === '');

  // Version info
  const versions = section.versions || [];
  const mainVersion = versions.find(v => v.is_main) || versions[0];
  const mainVersionNumber = mainVersion?.version_number || 1;
  const mainVersionId = mainVersion?.id || section.main_version_id;

  // Fetch all audio files for the song
  const { data: allAudioData, isLoading: isLoadingAudio } = useAudioFiles(songId);

  // Filter and group audio files by version for this section
  const audioByVersion = useMemo(() => {
    if (!allAudioData?.audio_files) return new Map<string, AudioFile[]>();

    const versionIds = new Set(versions.map(v => v.id));
    const sectionAudio = allAudioData.audio_files.filter(
      f => f.section_version_id && versionIds.has(f.section_version_id)
    );

    // Group by version
    const grouped = new Map<string, AudioFile[]>();
    for (const audio of sectionAudio) {
      const versionId = audio.section_version_id!;
      if (!grouped.has(versionId)) {
        grouped.set(versionId, []);
      }
      grouped.get(versionId)!.push(audio);
    }
    return grouped;
  }, [allAudioData, versions]);

  // Get total count across all versions
  const totalAudioCount = useMemo(() => {
    let count = 0;
    audioByVersion.forEach(files => count += files.length);
    return count;
  }, [audioByVersion]);

  // Sort versions for display: main version first, then by version number
  const sortedVersionsForAudio = useMemo(() => {
    return [...versions].sort((a, b) => {
      if (a.is_main && !b.is_main) return -1;
      if (!a.is_main && b.is_main) return 1;
      return a.version_number - b.version_number;
    });
  }, [versions]);

  // Drag and drop
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: section.id, disabled: !isDraggable });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  // Close dropdowns when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (versionDropdownRef.current && !versionDropdownRef.current.contains(event.target as Node)) {
        setIsVersionDropdownOpen(false);
      }
      if (audioPanelRef.current && !audioPanelRef.current.contains(event.target as Node)) {
        setIsAudioPanelOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleUploadAudio = useCallback((file: File) => {
    if (onUploadAudio && mainVersionId) {
      onUploadAudio(section.id, mainVersionId, file);
    }
  }, [onUploadAudio, section.id, mainVersionId]);

  return (
    <div
      ref={setNodeRef}
      style={style}
      id={`section-${section.id}`}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`
        mb-4 scroll-mt-4 relative
        ${onClick ? 'cursor-pointer' : ''}
        ${isSelected
          ? 'bg-indigo-50/50 dark:bg-indigo-900/10 border-l-2 border-indigo-500 pl-3 -ml-3'
          : 'border-l-2 border-transparent pl-3 -ml-3'}
        ${isDragging ? 'opacity-50 shadow-lg z-10' : ''}
        transition-all duration-150
      `}
    >
      {/* Section Header */}
      <div className="mb-1 flex items-center gap-2 group">
        {/* Drag Handle - show on hover when draggable */}
        {isDraggable && editable && (
          <div
            {...attributes}
            {...listeners}
            className={`
              cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600
              transition-opacity
              ${isHovered ? 'opacity-100' : 'opacity-0'}
            `}
            onClick={(e) => e.stopPropagation()}
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
            </svg>
          </div>
        )}

        {/* Section Label - click to edit type when editable */}
        {editable && onUpdateSection && isEditingType ? (
          <select
            value={section.type}
            onChange={(e) => {
              onUpdateSection(section.id, e.target.value as SectionType);
              setIsEditingType(false);
            }}
            onBlur={() => setIsEditingType(false)}
            onClick={(e) => e.stopPropagation()}
            autoFocus
            className="
              text-xs font-bold tracking-wider
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
            className={`
              text-xs font-bold tracking-wider
              px-2 py-0.5 rounded
              ${isSelected
                ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-100 dark:bg-indigo-900/30'
                : 'text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800'}
              ${editable && onUpdateSection ? 'cursor-pointer hover:ring-1 hover:ring-indigo-300' : ''}
            `}
            onClick={(e) => {
              if (editable && onUpdateSection) {
                e.stopPropagation();
                setIsEditingType(true);
              }
            }}
            title={editable && onUpdateSection ? 'Click to change section type' : undefined}
          >
            [{fullLabel}]
          </span>
        )}

        {/* Version Selector */}
        {editable && versions.length > 0 && (
          <div className="relative" ref={versionDropdownRef}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsVersionDropdownOpen(!isVersionDropdownOpen);
              }}
              className={`
                flex items-center gap-1 px-1.5 py-0.5
                text-[10px] font-medium
                rounded border
                transition-all
                bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600
                hover:bg-gray-200 dark:hover:bg-gray-600
                ${isHovered ? 'opacity-100' : 'opacity-60'}
              `}
              title="Switch version"
            >
              <span>v{mainVersionNumber}</span>
              {versions.length > 1 && (
                <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              )}
            </button>

            {/* Version Dropdown */}
            {isVersionDropdownOpen && (
              <div className="absolute left-0 top-full mt-1 z-20 min-w-36 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1">
                {versions.map((version) => (
                  <button
                    key={version.id}
                    className={`
                      w-full px-3 py-1.5 text-left flex items-center justify-between text-xs
                      ${version.is_main
                        ? 'bg-indigo-50 dark:bg-indigo-900/30'
                        : 'hover:bg-gray-50 dark:hover:bg-gray-750'
                      }
                    `}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (!version.is_main && onSwitchVersion) {
                        onSwitchVersion(section.id, version.id);
                      }
                      setIsVersionDropdownOpen(false);
                    }}
                    disabled={version.is_main}
                  >
                    <span className={`font-medium ${version.is_main ? 'text-indigo-700 dark:text-indigo-300' : 'text-gray-700 dark:text-gray-200'}`}>
                      v{version.version_number}
                    </span>
                    <span className="text-[10px] text-gray-400">
                      {version.line_count} lines
                    </span>
                  </button>
                ))}

                {onDuplicateVersion && mainVersionId && (
                  <>
                    <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDuplicateVersion(section.id, mainVersionId);
                        setIsVersionDropdownOpen(false);
                      }}
                      className="w-full px-3 py-1.5 text-left text-xs text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30"
                    >
                      + Duplicate to new version
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Audio Button - show on hover */}
        {editable && onUploadAudio && mainVersionId && (
          <div className="relative" ref={audioPanelRef}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setIsAudioPanelOpen(!isAudioPanelOpen);
              }}
              className={`
                p-1 rounded transition-all
                ${isAudioPanelOpen
                  ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                  : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700'
                }
                ${isHovered || isAudioPanelOpen ? 'opacity-100' : 'opacity-0'}
              `}
              title="Audio snippets"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
              </svg>
              {totalAudioCount > 0 && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-indigo-500 text-white text-[8px] rounded-full flex items-center justify-center">
                  {totalAudioCount}
                </span>
              )}
            </button>

            {/* Audio Panel Dropdown */}
            {isAudioPanelOpen && (
              <div className="absolute right-0 top-full mt-1 z-20 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-2 max-h-80 overflow-y-auto">
                <AudioUploadButton
                  onUpload={handleUploadAudio}
                  isUploading={isUploadingAudio}
                  compact
                />

                {isLoadingAudio && (
                  <div className="mt-2 text-xs text-gray-400 animate-pulse">Loading audio...</div>
                )}

                {totalAudioCount > 0 && (
                  <div className="mt-2 space-y-2">
                    {sortedVersionsForAudio.map((version) => {
                      const versionAudio = audioByVersion.get(version.id) || [];
                      if (versionAudio.length === 0) return null;

                      return (
                        <div key={version.id}>
                          {/* Version header */}
                          <div className={`
                            text-[10px] font-medium px-1.5 py-0.5 rounded mb-1
                            ${version.is_main
                              ? 'text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/30'
                              : 'text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700'
                            }
                          `}>
                            v{version.version_number}
                            {version.is_main && ' (current)'}
                            <span className="text-gray-400 dark:text-gray-500 ml-1">
                              · {versionAudio.length} file{versionAudio.length !== 1 ? 's' : ''}
                            </span>
                          </div>
                          {/* Audio files for this version */}
                          <div className="space-y-1">
                            {versionAudio.map((audioFile) => (
                              <VersionAudioItem key={audioFile.id} audioFile={audioFile} songId={songId} compact />
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {totalAudioCount === 0 && !isLoadingAudio && (
                  <div className="mt-2 text-xs text-gray-400 dark:text-gray-500 text-center py-2">
                    No audio files yet
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Delete section button - show on hover */}
        {editable && onDeleteSection && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDeleteSection(section.id);
            }}
            className={`
              p-1 rounded text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20
              transition-all
              ${isHovered ? 'opacity-100' : 'opacity-0'}
            `}
            title="Delete section"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>

      {/* Lines */}
      <div className="font-mono text-sm pl-1">
        {section.lines.length === 0 ? (
          <p className="text-gray-400 dark:text-gray-500 italic text-xs">
            (empty section)
          </p>
        ) : (
          section.lines.map((line, index) =>
            canEdit ? (
              <EditableLineDisplay
                key={line.id}
                line={line}
                sectionId={section.id}
                lineIndex={index}
                isFirstLine={index === 0}
                isLastLine={index === section.lines.length - 1}
                isOnlyLine={section.lines.length === 1}
                isSectionEmpty={isSectionEmpty}
                isFirstSection={isFirst}
                showChords={showChords}
                onAddChord={onAddChord}
                onRemoveChord={onRemoveChord}
                onUpdateLine={onUpdateLine}
                onAddLineAfter={onAddLineAfter}
                onDeleteLine={onDeleteLine}
                onMergeWithPrevious={onMergeWithPrevious}
                onAddSectionAfter={onAddSectionAfter}
                onDeleteSection={onDeleteSection}
                shouldFocus={focusLineId === line.id}
                focusCursorPosition={focusCursorPosition}
                onFocusHandled={onFocusHandled}
              />
            ) : (
              <LineDisplay key={line.id} line={line} showChords={showChords} />
            )
          )
        )}
      </div>
    </div>
  );
}
