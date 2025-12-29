'use client';

/**
 * Canvas Editor Hook
 *
 * Manages canvas editor state including lines, focus, and operations.
 */

import { useState, useCallback, useRef, useLayoutEffect } from 'react';
import { LineType, Song, Section } from '@/types/song';
import { CanvasLine } from './types';

interface UseCanvasEditorOptions {
  song: Song;
  onSave?: (lines: CanvasLine[]) => void;
}

interface PendingFocus {
  lineId: string;
  cursorPosition: number | 'end';
}

interface UseCanvasEditorReturn {
  lines: CanvasLine[];
  focusedLineId: string | null;
  setFocusedLineId: (id: string | null) => void;
  updateLineText: (id: string, text: string) => void;
  updateLineType: (id: string, lineType: LineType) => void;
  insertLineAfter: (id: string, cursorPosition: number) => void;
  deleteLine: (id: string) => void;
  focusPreviousLine: (id: string) => void;
  focusNextLine: (id: string) => void;
  focusLine: (id: string) => void;
  isDirty: boolean;
}

/**
 * Flatten a song's sections into a flat list of canvas lines.
 */
function flattenSong(song: Song): CanvasLine[] {
  const lines: CanvasLine[] = [];
  let order = 0;

  for (const section of song.sections) {
    // Add section header as a line
    const headerText = formatSectionHeader(section);
    lines.push({
      id: `header-${section.id}`,
      lineType: LineType.SECTION_HEADER,
      text: headerText,
      order: order++,
    });

    // Add lines from the section
    for (const line of section.lines) {
      lines.push({
        id: line.id,
        lineType: line.line_type || LineType.LYRIC,
        text: line.text,
        order: order++,
      });
    }
  }

  // If song has no sections, add an empty lyric line
  if (lines.length === 0) {
    lines.push({
      id: 'new-line-1',
      lineType: LineType.LYRIC,
      text: '',
      order: 0,
    });
  }

  return lines;
}

/**
 * Format a section into a header text.
 */
function formatSectionHeader(section: Section): string {
  const typeName = section.type.charAt(0).toUpperCase() + section.type.slice(1).replace('_', ' ');
  if (section.number && section.number > 0) {
    return `${typeName} ${section.number}`;
  }
  return typeName;
}

/**
 * Generate a unique ID for a new line.
 */
function generateLineId(): string {
  return `new-line-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function useCanvasEditor({
  song,
}: UseCanvasEditorOptions): UseCanvasEditorReturn {
  const [lines, setLines] = useState<CanvasLine[]>(() => flattenSong(song));
  const [focusedLineId, setFocusedLineId] = useState<string | null>(null);
  const [isDirty, setIsDirty] = useState(false);

  // Use a ref for pending focus - the effect will process it when lines change
  const pendingFocusRef = useRef<PendingFocus | null>(null);

  // Apply pending focus after lines change and DOM updates
  // useLayoutEffect runs synchronously after DOM mutations but before paint
  useLayoutEffect(() => {
    if (pendingFocusRef.current) {
      const { lineId, cursorPosition } = pendingFocusRef.current;

      const input = document.querySelector(
        `[data-line-id="${lineId}"] input`
      ) as HTMLInputElement;

      if (input) {
        input.focus();
        const pos = cursorPosition === 'end' ? input.value.length : cursorPosition;
        input.setSelectionRange(pos, pos);
        setFocusedLineId(lineId);
        pendingFocusRef.current = null;
      }
      // If element not found, keep pending focus for next render
    }
  }, [lines]);

  const scheduleFocus = useCallback((lineId: string, cursorPosition: number | 'end') => {
    pendingFocusRef.current = { lineId, cursorPosition };
  }, []);

  const updateLineText = useCallback((id: string, text: string) => {
    setLines((prev) =>
      prev.map((line) => (line.id === id ? { ...line, text } : line))
    );
    setIsDirty(true);
  }, []);

  const updateLineType = useCallback((id: string, lineType: LineType) => {
    setLines((prev) =>
      prev.map((line) => (line.id === id ? { ...line, lineType } : line))
    );
    setIsDirty(true);
  }, []);

  const insertLineAfter = useCallback((id: string, cursorPosition: number) => {
    const newLineId = generateLineId();

    setLines((prev) => {
      const index = prev.findIndex((line) => line.id === id);
      if (index === -1) {
        console.warn('insertLineAfter: line not found', id);
        return prev;
      }

      const currentLine = prev[index];
      const textBefore = currentLine.text.slice(0, cursorPosition);
      const textAfter = currentLine.text.slice(cursorPosition);

      const newLines = [...prev];
      // Update current line with text before cursor
      newLines[index] = { ...currentLine, text: textBefore };
      // Insert new line with text after cursor
      newLines.splice(index + 1, 0, {
        id: newLineId,
        lineType: LineType.LYRIC,
        text: textAfter,
        order: 0,
      });

      // Reorder all lines
      return newLines.map((line, i) => ({ ...line, order: i }));
    });

    setIsDirty(true);
    scheduleFocus(newLineId, 0);
  }, [scheduleFocus]);

  const deleteLine = useCallback((id: string) => {
    setLines((prev) => {
      const index = prev.findIndex((line) => line.id === id);
      if (index === -1) return prev;

      // Don't delete if it's the only line
      if (prev.length === 1) return prev;

      // Focus the previous line, or the next if this is the first
      const focusIndex = index > 0 ? index - 1 : 1;
      const focusId = prev[focusIndex].id;

      // Schedule focus before modifying array
      pendingFocusRef.current = { lineId: focusId, cursorPosition: 'end' };

      const newLines = prev.filter((line) => line.id !== id);
      return newLines.map((line, i) => ({ ...line, order: i }));
    });

    setIsDirty(true);
  }, []);

  // For arrow key navigation, focus immediately (line already exists in DOM)
  const focusLineImmediate = useCallback((lineId: string, cursorPosition: number | 'end') => {
    const input = document.querySelector(
      `[data-line-id="${lineId}"] input`
    ) as HTMLInputElement;

    if (input) {
      input.focus();
      const pos = cursorPosition === 'end' ? input.value.length : cursorPosition;
      input.setSelectionRange(pos, pos);
      setFocusedLineId(lineId);
    }
  }, []);

  const focusPreviousLine = useCallback((id: string) => {
    const index = lines.findIndex((line) => line.id === id);
    if (index > 0) {
      focusLineImmediate(lines[index - 1].id, 'end');
    }
  }, [lines, focusLineImmediate]);

  const focusNextLine = useCallback((id: string) => {
    const index = lines.findIndex((line) => line.id === id);
    if (index < lines.length - 1) {
      focusLineImmediate(lines[index + 1].id, 0);
    }
  }, [lines, focusLineImmediate]);

  const focusLine = useCallback((id: string) => {
    focusLineImmediate(id, 0);
  }, [focusLineImmediate]);

  return {
    lines,
    focusedLineId,
    setFocusedLineId,
    updateLineText,
    updateLineType,
    insertLineAfter,
    deleteLine,
    focusPreviousLine,
    focusNextLine,
    focusLine,
    isDirty,
  };
}
