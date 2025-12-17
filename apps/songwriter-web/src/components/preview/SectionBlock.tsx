'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Section, SectionType, Line, ChordPlacement } from '@/types';
import { ChordEditor } from './ChordEditor';

interface SectionBlockProps {
  section: Section;
  isSelected?: boolean;
  onClick?: () => void;
  /** Enable chord editing mode */
  editable?: boolean;
  /** Called when a new chord is added */
  onAddChord?: (sectionId: string, lineId: string, chord: string, position: number) => void;
  /** Called when a chord is removed */
  onRemoveChord?: (sectionId: string, lineId: string, position: number) => void;
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
  onAddChord: (sectionId: string, lineId: string, chord: string, position: number) => void;
  onRemoveChord: (sectionId: string, lineId: string, position: number) => void;
}

function EditableLineDisplay({ line, sectionId, onAddChord, onRemoveChord }: EditableLineDisplayProps) {
  const [editorState, setEditorState] = useState<{
    position: number;
    anchorX: number;
    anchorY: number;
    existingChord?: ChordPlacement;
  } | null>(null);

  const [hoverPosition, setHoverPosition] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const textRef = useRef<HTMLDivElement>(null);

  // Get accurate character width for monospace font
  const charWidth = useCharWidth(containerRef);

  // Find chord at a given position
  const findChordAtPosition = useCallback((pos: number): ChordPlacement | undefined => {
    return line.chords.find(c => pos >= c.position && pos < c.position + c.chord.length);
  }, [line.chords]);

  // Calculate character position from click/mouse event
  const getCharPositionFromEvent = useCallback((e: React.MouseEvent<HTMLDivElement>): number => {
    if (!containerRef.current) return 0;

    const containerRect = containerRef.current.getBoundingClientRect();
    const clickX = e.clientX - containerRect.left;
    const position = Math.max(0, Math.floor(clickX / charWidth));

    return position;
  }, [charWidth]);

  // Handle click to add/edit chord
  const handleClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation();

    const position = getCharPositionFromEvent(e);
    const existingChord = findChordAtPosition(position);

    // Calculate anchor position for the popover
    const containerRect = containerRef.current?.getBoundingClientRect();
    const anchorX = containerRect ? containerRect.left + (position * charWidth) + (charWidth / 2) : e.clientX;
    const anchorY = containerRect?.top ?? e.clientY;

    setEditorState({
      position: existingChord ? existingChord.position : position,
      anchorX,
      anchorY,
      existingChord,
    });
    setHoverPosition(null);
  }, [getCharPositionFromEvent, findChordAtPosition, charWidth]);

  // Track mouse position for visual feedback
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (editorState) return; // Don't show hover when editor is open
    const position = getCharPositionFromEvent(e);
    setHoverPosition(position);
  }, [getCharPositionFromEvent, editorState]);

  const handleMouseLeave = useCallback(() => {
    setHoverPosition(null);
  }, []);

  const handleSaveChord = useCallback(async (chord: string) => {
    if (editorState) {
      // The backend handles both add and update at the same position
      // So we just call addChord - it will update if a chord exists at that position
      await onAddChord(sectionId, line.id, chord, editorState.position);
    }
    setEditorState(null);
  }, [editorState, sectionId, line.id, onAddChord]);

  const handleDeleteChord = useCallback(async () => {
    if (editorState?.existingChord) {
      await onRemoveChord(sectionId, line.id, editorState.existingChord.position);
    }
    setEditorState(null);
  }, [editorState, sectionId, line.id, onRemoveChord]);

  const chordLine = renderChordLine(line.text, line.chords);

  // Build the chord line with hover indicator
  const renderChordLineWithIndicator = () => {
    if (hoverPosition === null || editorState) {
      return chordLine || '\u00A0';
    }

    // Check if there's already a chord at hover position
    const existingChord = findChordAtPosition(hoverPosition);
    if (existingChord) {
      return chordLine || '\u00A0';
    }

    // Insert a visual indicator at the hover position
    const chars = (chordLine || '').split('');
    // Pad to hover position if needed
    while (chars.length <= hoverPosition) {
      chars.push(' ');
    }

    // Only show indicator if position is empty
    if (chars[hoverPosition] === ' ' || chars[hoverPosition] === undefined) {
      chars[hoverPosition] = '│';
    }

    return chars.join('') || '\u00A0';
  };

  return (
    <div
      ref={containerRef}
      className="leading-relaxed group relative"
      onClick={handleClick}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
    >
      {/* Chord line - always show for click target */}
      <div
        className={`
          text-indigo-600 dark:text-indigo-400 font-bold whitespace-pre
          min-h-[1.5em] cursor-pointer
          hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded
          transition-colors
          ${!chordLine && hoverPosition === null ? 'opacity-0 group-hover:opacity-50' : ''}
        `}
        title="Click to add or edit chord"
      >
        {renderChordLineWithIndicator()}
      </div>

      {/* Lyric line */}
      <div
        ref={textRef}
        className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap cursor-pointer"
        title="Click to add chord at this position"
      >
        {line.text || '\u00A0'}
      </div>

      {/* Chord editor popover */}
      {editorState && (
        <ChordEditor
          initialChord={editorState.existingChord?.chord || ''}
          anchorPosition={{ x: editorState.anchorX, y: editorState.anchorY }}
          onSave={handleSaveChord}
          onDelete={editorState.existingChord ? handleDeleteChord : undefined}
          onClose={() => setEditorState(null)}
        />
      )}
    </div>
  );
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

export function SectionBlock({
  section,
  isSelected,
  onClick,
  editable = false,
  onAddChord,
  onRemoveChord,
}: SectionBlockProps) {
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
          section.lines.map((line) =>
            editable && onAddChord && onRemoveChord ? (
              <EditableLineDisplay
                key={line.id}
                line={line}
                sectionId={section.id}
                onAddChord={onAddChord}
                onRemoveChord={onRemoveChord}
              />
            ) : (
              <LineDisplay key={line.id} line={line} />
            )
          )
        )}
      </div>
    </div>
  );
}
