'use client';

import { useState, useRef, useCallback } from 'react';
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

  const textRef = useRef<HTMLDivElement>(null);
  const chordLineRef = useRef<HTMLDivElement>(null);

  // Find chord at a given position
  const findChordAtPosition = useCallback((pos: number): ChordPlacement | undefined => {
    return line.chords.find(c => pos >= c.position && pos < c.position + c.chord.length);
  }, [line.chords]);

  // Handle click on the chord line area (above text)
  const handleChordLineClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation();

    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;

    // Calculate character position based on monospace font
    // We need to measure the actual character width
    const charWidth = textRef.current
      ? textRef.current.getBoundingClientRect().width / Math.max(line.text.length, 1)
      : 8; // fallback

    const position = Math.floor(clickX / charWidth);

    // Check if there's an existing chord at this position
    const existingChord = findChordAtPosition(position);

    setEditorState({
      position: existingChord ? existingChord.position : position,
      anchorX: e.clientX,
      anchorY: rect.top,
      existingChord,
    });
  }, [line.text.length, findChordAtPosition]);

  // Handle click on the text line (shows guide)
  const handleTextClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.stopPropagation();

    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;

    // Calculate character position
    const charWidth = rect.width / Math.max(line.text.length, 1);
    const position = Math.floor(clickX / charWidth);

    // Check if there's an existing chord at this position
    const existingChord = findChordAtPosition(position);

    setEditorState({
      position: existingChord ? existingChord.position : position,
      anchorX: e.clientX,
      anchorY: rect.top,
      existingChord,
    });
  }, [line.text.length, findChordAtPosition]);

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

  return (
    <div className="leading-relaxed group">
      {/* Chord line - always show (even if empty) for click target */}
      <div
        ref={chordLineRef}
        onClick={handleChordLineClick}
        className={`
          text-indigo-600 dark:text-indigo-400 font-bold whitespace-pre
          min-h-[1.5em] cursor-pointer
          hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded
          transition-colors
          ${!chordLine ? 'opacity-0 group-hover:opacity-50' : ''}
        `}
        title="Click to add or edit chord"
      >
        {chordLine || '\u00A0'}
      </div>

      {/* Lyric line */}
      <div
        ref={textRef}
        onClick={handleTextClick}
        className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded transition-colors"
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
