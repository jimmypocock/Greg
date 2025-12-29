'use client';

/**
 * Canvas Line
 *
 * A single line in the canvas editor with type-aware styling,
 * prefix detection, and backspace-to-revert behavior.
 */

import { useRef, useCallback, KeyboardEvent, ChangeEvent } from 'react';
import { LineType } from '@/types/song';
import { CanvasLineGutter } from './CanvasLineGutter';
import {
  LINE_TYPE_CONFIGS,
  detectPrefixAndTransform,
  getPrefixForType,
} from './types';

interface CanvasLineProps {
  id: string;
  lineType: LineType;
  text: string;
  isFocused?: boolean;
  onTextChange: (id: string, text: string) => void;
  onTypeChange: (id: string, newType: LineType) => void;
  onFocus: (id: string) => void;
  onBlur: (id: string) => void;
  onEnter: (id: string, cursorPosition: number) => void;
  onBackspaceAtStart: (id: string) => void;
  onArrowUp: (id: string) => void;
  onArrowDown: (id: string) => void;
}

export function CanvasLine({
  id,
  lineType,
  text,
  isFocused,
  onTextChange,
  onTypeChange,
  onFocus,
  onBlur,
  onEnter,
  onBackspaceAtStart,
  onArrowUp,
  onArrowDown,
}: CanvasLineProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const config = LINE_TYPE_CONFIGS[lineType];

  // Track if we're in the middle of reverting (to prevent double-revert)
  const isRevertingRef = useRef(false);

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const newText = e.target.value;

      // Check for prefix transformation
      const transform = detectPrefixAndTransform(newText);
      if (transform && transform.lineType !== lineType) {
        // Transform the line type and update text
        onTypeChange(id, transform.lineType);
        onTextChange(id, transform.cleanedText);
        return;
      }

      onTextChange(id, newText);
    },
    [id, lineType, onTextChange, onTypeChange]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      const input = inputRef.current;
      if (!input) return;

      const cursorPosition = input.selectionStart ?? 0;
      const selectionEnd = input.selectionEnd ?? 0;
      const hasSelection = cursorPosition !== selectionEnd;

      // Enter: Split line or create new line
      if (e.key === 'Enter') {
        e.preventDefault();
        onEnter(id, cursorPosition);
        return;
      }

      // Backspace at start: Revert line type or merge with previous
      if (e.key === 'Backspace' && cursorPosition === 0 && !hasSelection) {
        // If not a lyric, revert to lyric and restore prefix
        if (lineType !== LineType.LYRIC && !isRevertingRef.current) {
          e.preventDefault();
          isRevertingRef.current = true;

          const prefix = getPrefixForType(lineType);
          onTypeChange(id, LineType.LYRIC);
          onTextChange(id, prefix + text);

          // Move cursor after prefix
          requestAnimationFrame(() => {
            if (inputRef.current) {
              inputRef.current.setSelectionRange(prefix.length, prefix.length);
            }
            isRevertingRef.current = false;
          });
          return;
        }

        // If already a lyric and at start, merge with previous line
        if (lineType === LineType.LYRIC && text === '') {
          e.preventDefault();
          onBackspaceAtStart(id);
          return;
        }
      }

      // Arrow up: Move to previous line
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        onArrowUp(id);
        return;
      }

      // Arrow down: Move to next line
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        onArrowDown(id);
        return;
      }
    },
    [id, lineType, text, onEnter, onBackspaceAtStart, onArrowUp, onArrowDown, onTypeChange, onTextChange]
  );

  const handleTypeChangeFromGutter = useCallback(
    (newType: LineType) => {
      onTypeChange(id, newType);
      // Focus the input after changing type
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    },
    [id, onTypeChange]
  );

  return (
    <div
      className={`
        flex items-center group leading-tight
        ${isFocused ? 'bg-blue-50/30 dark:bg-blue-950/10' : ''}
      `}
    >
      <CanvasLineGutter
        lineType={lineType}
        onTypeChange={handleTypeChangeFromGutter}
      />

      <input
        ref={inputRef}
        type="text"
        value={text}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={() => onFocus(id)}
        onBlur={() => onBlur(id)}
        placeholder={config.placeholder}
        className={`
          flex-1 py-0.5 px-0
          bg-transparent
          border-none outline-none
          placeholder:text-gray-300 dark:placeholder:text-gray-600
          ${config.className || ''}
        `}
        aria-label={`${config.label} line`}
      />
    </div>
  );
}
