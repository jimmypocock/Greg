'use client';

/**
 * Canvas Editor
 *
 * A flat, document-style song editor that treats songs as lists of lines.
 * Supports different line types (lyric, chord, section_header, annotation)
 * with markdown-like prefix detection.
 */

import { useCallback } from 'react';
import { Song } from '@/types/song';
import { CanvasLine } from './CanvasLine';
import { useCanvasEditor } from './useCanvasEditor';

interface CanvasEditorProps {
  song: Song;
  onSave?: () => void;
}

export function CanvasEditor({ song, onSave }: CanvasEditorProps) {
  const {
    lines,
    focusedLineId,
    setFocusedLineId,
    updateLineText,
    updateLineType,
    insertLineAfter,
    deleteLine,
    focusPreviousLine,
    focusNextLine,
  } = useCanvasEditor({ song });

  const handleFocus = useCallback(
    (id: string) => {
      setFocusedLineId(id);
    },
    [setFocusedLineId]
  );

  const handleBlur = useCallback(
    (id: string) => {
      // Only clear focus if this line is still focused
      if (focusedLineId === id) {
        setFocusedLineId(null);
      }
    },
    [focusedLineId, setFocusedLineId]
  );

  const handleEnter = useCallback(
    (id: string, cursorPosition: number) => {
      insertLineAfter(id, cursorPosition);
    },
    [insertLineAfter]
  );

  const handleBackspaceAtStart = useCallback(
    (id: string) => {
      deleteLine(id);
    },
    [deleteLine]
  );

  return (
    <div className="canvas-editor w-full max-w-3xl mx-auto font-mono text-sm">
      {/* Header with hints */}
      <div className="mb-2 ml-6 text-xs text-gray-400 dark:text-gray-500 flex gap-3">
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">#</code> section
        </span>
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">&gt;</code> chord
        </span>
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">//</code> note
        </span>
      </div>

      {/* Lines */}
      <div>
        {lines.map((line) => (
          <div key={line.id} data-line-id={line.id}>
            <CanvasLine
              id={line.id}
              lineType={line.lineType}
              text={line.text}
              isFocused={focusedLineId === line.id}
              onTextChange={updateLineText}
              onTypeChange={updateLineType}
              onFocus={handleFocus}
              onBlur={handleBlur}
              onEnter={handleEnter}
              onBackspaceAtStart={handleBackspaceAtStart}
              onArrowUp={focusPreviousLine}
              onArrowDown={focusNextLine}
            />
          </div>
        ))}
      </div>

      {/* Footer hints */}
      <div className="mt-1 ml-6 text-xs text-gray-400 dark:text-gray-500">
        Enter = new line · Click icon to change type
      </div>
    </div>
  );
}
