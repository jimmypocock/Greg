'use client';

/**
 * Yjs Song Data Hook
 *
 * Wraps useYjsSong and converts the Yjs document to a Song interface.
 * Provides functions to mutate the Yjs document directly.
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import * as Y from 'yjs';
import { useYjsSong, ConnectionStatus } from './useYjsSong';
import {
  Song,
  Section,
  Line,
  LineType,
  SectionType,
  SongStatus,
  ChordPlacement,
} from '@/types';

// Convert Yjs line to Line interface
function yjsLineToLine(yjsLine: Y.Map<unknown>, order: number): Line {
  const chordsArray = yjsLine.get('chords') as Y.Array<unknown> | undefined;
  const chords: ChordPlacement[] = chordsArray
    ? chordsArray.toArray().map((c: unknown) => {
        const chord = c as Y.Map<unknown>;
        return {
          id: (chord.get('id') as string) || crypto.randomUUID(),
          chord: (chord.get('chord') as string) || '',
          position: (chord.get('position') as number) || 0,
        };
      })
    : [];

  return {
    id: (yjsLine.get('id') as string) || '',
    line_type: (yjsLine.get('line_type') as LineType) || LineType.LYRIC,
    text: (yjsLine.get('text') as string) || '',
    order,
    notes: yjsLine.get('notes') as string | null,
    chords,
  };
}

// Convert Yjs section to Section interface
function yjsSectionToSection(yjsSection: Y.Map<unknown>, order: number): Section {
  const linesArray = yjsSection.get('lines') as Y.Array<unknown> | undefined;
  const lines: Line[] = linesArray
    ? linesArray.toArray().map((l: unknown, i: number) => {
        return yjsLineToLine(l as Y.Map<unknown>, i);
      })
    : [];

  return {
    id: (yjsSection.get('id') as string) || '',
    song_id: (yjsSection.get('song_id') as string) || '',
    type: (yjsSection.get('type') as SectionType) || SectionType.VERSE,
    number: yjsSection.get('number') as number | undefined,
    order,
    lines,
    versions: [], // Versions not synced via Yjs yet
    main_version_id: null,
    notes: yjsSection.get('notes') as string | null,
    created_at: (yjsSection.get('created_at') as string) || new Date().toISOString(),
  };
}

// Convert Yjs document to Song interface
function yjsDocToSong(doc: Y.Doc): Song | null {
  try {
    const meta = doc.getMap('meta');
    const sectionsArray = doc.getArray('sections');

    const id = meta.get('id') as string;
    if (!id) {
      return null; // Document not yet populated
    }

    const sections: Section[] = sectionsArray.toArray().map((s: unknown, i: number) => {
      return yjsSectionToSection(s as Y.Map<unknown>, i);
    });

    return {
      id,
      title: (meta.get('title') as string) || 'Untitled',
      raw_input: meta.get('raw_input') as string | undefined,
      key: meta.get('key') as string | undefined,
      tempo: meta.get('tempo') as number | undefined,
      time_signature: (meta.get('time_signature') as string) || '4/4',
      feel: meta.get('feel') as string | undefined,
      sections,
      song_notes: [], // Notes not synced via Yjs yet
      status: (meta.get('status') as SongStatus) || SongStatus.DRAFT,
      notes: meta.get('notes') as string | undefined,
      created_at: (meta.get('created_at') as string) || new Date().toISOString(),
      updated_at: (meta.get('updated_at') as string) || new Date().toISOString(),
    };
  } catch (err) {
    console.error('Error converting Yjs document to Song:', err);
    return null;
  }
}

export interface YjsSongDataState {
  /** The song data from Yjs document */
  song: Song | null;
  /** Whether the initial sync is still loading */
  isLoading: boolean;
  /** Connection status */
  status: ConnectionStatus;
  /** Error message if any */
  error: string | null;
  /** Number of connected users */
  connectedUsers: number;
  /** Reconnect to WebSocket */
  reconnect: () => void;
  /** Disconnect from WebSocket */
  disconnect: () => void;
  /** Access to the underlying Yjs document for direct manipulation */
  doc: Y.Doc | null;
  /** Update a line's text */
  updateLine: (sectionId: string, lineId: string, text: string) => void;
  /** Add a new line to a section */
  addLine: (sectionId: string, text: string, afterLineId?: string) => string | undefined;
  /** Delete a line */
  deleteLine: (sectionId: string, lineId: string) => void;
  /** Add a new section */
  addSection: (type: SectionType, afterSectionId?: string) => string | undefined;
  /** Delete a section */
  deleteSection: (sectionId: string) => void;
  /** Update section type */
  updateSection: (sectionId: string, type: SectionType, number?: number) => void;
  /** Update song metadata */
  updateMeta: (updates: Partial<Pick<Song, 'title' | 'key' | 'tempo' | 'time_signature' | 'status' | 'notes'>>) => void;
  /** Add a chord to a line */
  addChord: (sectionId: string, lineId: string, chord: string, position: number) => void;
  /** Remove a chord from a line */
  removeChord: (sectionId: string, lineId: string, position: number) => void;
  /** Reorder sections */
  reorderSections: (sectionIds: string[]) => void;
  /** Reorder lines within a section */
  reorderLines: (sectionId: string, lineIds: string[]) => void;
}

export interface UseYjsSongDataOptions {
  songId: string;
  /** Initial song data from REST API (used while Yjs syncs) */
  initialSong?: Song | null;
  /** Whether to auto-connect to WebSocket (default: true) */
  autoConnect?: boolean;
}

export function useYjsSongData({
  songId,
  initialSong,
  autoConnect = true,
}: UseYjsSongDataOptions): YjsSongDataState {
  const [song, setSong] = useState<Song | null>(initialSong || null);
  const [isLoading, setIsLoading] = useState(autoConnect);
  const [hasSynced, setHasSynced] = useState(!autoConnect);

  // Sync handler
  const handleSync = useCallback((doc: Y.Doc) => {
    const songData = yjsDocToSong(doc);
    if (songData) {
      setSong(songData);
      setHasSynced(true);
    }
    setIsLoading(false);
  }, []);

  const {
    doc,
    status,
    error,
    connectedUsers,
    reconnect,
    disconnect,
  } = useYjsSong({
    songId,
    autoConnect,
    onSync: handleSync,
  });

  // Update song state when Yjs document changes
  useEffect(() => {
    if (!doc) {
      console.log('[Yjs] No doc yet, skipping observer setup');
      return;
    }

    console.log('[Yjs] Setting up observers on doc');

    const updateFromDoc = () => {
      console.log('[Yjs] Observer fired - updating song from doc');
      const songData = yjsDocToSong(doc);
      if (songData) {
        console.log('[Yjs] Song data updated:', songData.title, 'sections:', songData.sections.length);
        setSong(songData);
      }
    };

    // Observe meta changes
    const meta = doc.getMap('meta');
    meta.observe(updateFromDoc);

    // Observe sections changes (deep)
    const sections = doc.getArray('sections');
    sections.observeDeep(updateFromDoc);

    // Initial read
    updateFromDoc();

    return () => {
      console.log('[Yjs] Cleaning up observers');
      meta.unobserve(updateFromDoc);
      sections.unobserveDeep(updateFromDoc);
    };
  }, [doc]);

  // Helper to find section by ID
  const findSection = useCallback((sectionId: string): { section: Y.Map<unknown>; index: number } | null => {
    if (!doc) return null;
    const sections = doc.getArray('sections');
    for (let i = 0; i < sections.length; i++) {
      const section = sections.get(i) as Y.Map<unknown>;
      if (section.get('id') === sectionId) {
        return { section, index: i };
      }
    }
    return null;
  }, [doc]);

  // Helper to find line by ID within a section
  const findLine = useCallback((section: Y.Map<unknown>, lineId: string): { line: Y.Map<unknown>; index: number } | null => {
    const lines = section.get('lines') as Y.Array<unknown>;
    if (!lines) return null;
    for (let i = 0; i < lines.length; i++) {
      const line = lines.get(i) as Y.Map<unknown>;
      if (line.get('id') === lineId) {
        return { line, index: i };
      }
    }
    return null;
  }, []);

  // Update line text
  const updateLine = useCallback((sectionId: string, lineId: string, text: string) => {
    console.log('[Yjs] updateLine called:', { sectionId, lineId, text });
    const result = findSection(sectionId);
    if (!result) {
      console.log('[Yjs] Section not found:', sectionId);
      return;
    }

    const lineResult = findLine(result.section, lineId);
    if (!lineResult) {
      console.log('[Yjs] Line not found:', lineId);
      return;
    }

    console.log('[Yjs] Setting text on line');
    lineResult.line.set('text', text);
  }, [findSection, findLine]);

  // Add a new line
  const addLine = useCallback((sectionId: string, text: string, afterLineId?: string): string | undefined => {
    const result = findSection(sectionId);
    if (!result) return;

    const lines = result.section.get('lines') as Y.Array<unknown>;
    if (!lines) return;

    const newLine = new Y.Map();
    const newId = crypto.randomUUID();
    newLine.set('id', newId);
    newLine.set('text', text);
    newLine.set('line_type', LineType.LYRIC);
    newLine.set('chords', new Y.Array());

    if (afterLineId) {
      const afterResult = findLine(result.section, afterLineId);
      if (afterResult) {
        lines.insert(afterResult.index + 1, [newLine]);
      } else {
        lines.push([newLine]);
      }
    } else {
      lines.push([newLine]);
    }

    return newId;
  }, [findSection, findLine]);

  // Delete a line
  const deleteLine = useCallback((sectionId: string, lineId: string) => {
    const result = findSection(sectionId);
    if (!result) return;

    const lines = result.section.get('lines') as Y.Array<unknown>;
    if (!lines) return;

    const lineResult = findLine(result.section, lineId);
    if (!lineResult) return;

    lines.delete(lineResult.index, 1);
  }, [findSection, findLine]);

  // Add a new section
  const addSection = useCallback((type: SectionType, afterSectionId?: string): string | undefined => {
    if (!doc) return;

    const sections = doc.getArray('sections');
    const newSection = new Y.Map();
    const newId = crypto.randomUUID();

    newSection.set('id', newId);
    newSection.set('song_id', songId);
    newSection.set('type', type);
    newSection.set('created_at', new Date().toISOString());

    // Add an empty line
    const lines = new Y.Array();
    const firstLine = new Y.Map();
    firstLine.set('id', crypto.randomUUID());
    firstLine.set('text', '');
    firstLine.set('line_type', LineType.LYRIC);
    firstLine.set('chords', new Y.Array());
    lines.push([firstLine]);
    newSection.set('lines', lines);

    if (afterSectionId) {
      const afterResult = findSection(afterSectionId);
      if (afterResult) {
        sections.insert(afterResult.index + 1, [newSection]);
      } else {
        sections.push([newSection]);
      }
    } else {
      sections.push([newSection]);
    }

    return newId;
  }, [doc, songId, findSection]);

  // Delete a section
  const deleteSection = useCallback((sectionId: string) => {
    if (!doc) return;

    const result = findSection(sectionId);
    if (!result) return;

    const sections = doc.getArray('sections');
    sections.delete(result.index, 1);
  }, [doc, findSection]);

  // Update section type
  const updateSection = useCallback((sectionId: string, type: SectionType, number?: number) => {
    const result = findSection(sectionId);
    if (!result) return;

    result.section.set('type', type);
    if (number !== undefined) {
      result.section.set('number', number);
    }
  }, [findSection]);

  // Update song metadata
  const updateMeta = useCallback((updates: Partial<Pick<Song, 'title' | 'key' | 'tempo' | 'time_signature' | 'status' | 'notes'>>) => {
    if (!doc) return;

    const meta = doc.getMap('meta');
    Object.entries(updates).forEach(([key, value]) => {
      if (value !== undefined) {
        meta.set(key, value);
      }
    });
    meta.set('updated_at', new Date().toISOString());
  }, [doc]);

  // Add a chord to a line
  const addChord = useCallback((sectionId: string, lineId: string, chord: string, position: number) => {
    const result = findSection(sectionId);
    if (!result) return;

    const lineResult = findLine(result.section, lineId);
    if (!lineResult) return;

    let chords = lineResult.line.get('chords') as Y.Array<unknown>;
    if (!chords) {
      chords = new Y.Array();
      lineResult.line.set('chords', chords);
    }

    const newChord = new Y.Map();
    newChord.set('id', crypto.randomUUID());
    newChord.set('chord', chord);
    newChord.set('position', position);
    chords.push([newChord]);
  }, [findSection, findLine]);

  // Remove a chord from a line
  const removeChord = useCallback((sectionId: string, lineId: string, position: number) => {
    const result = findSection(sectionId);
    if (!result) return;

    const lineResult = findLine(result.section, lineId);
    if (!lineResult) return;

    const chords = lineResult.line.get('chords') as Y.Array<unknown>;
    if (!chords) return;

    for (let i = 0; i < chords.length; i++) {
      const chord = chords.get(i) as Y.Map<unknown>;
      if (chord.get('position') === position) {
        chords.delete(i, 1);
        break;
      }
    }
  }, [findSection, findLine]);

  // Reorder sections
  const reorderSections = useCallback((sectionIds: string[]) => {
    if (!doc) return;

    const sections = doc.getArray('sections');
    const currentSections: Y.Map<unknown>[] = [];

    // Collect all sections
    for (let i = 0; i < sections.length; i++) {
      currentSections.push(sections.get(i) as Y.Map<unknown>);
    }

    // Create a map of id -> section
    const sectionMap = new Map<string, Y.Map<unknown>>();
    currentSections.forEach(s => {
      sectionMap.set(s.get('id') as string, s);
    });

    // Reorder based on sectionIds
    doc.transact(() => {
      // Clear and re-add in new order
      while (sections.length > 0) {
        sections.delete(0, 1);
      }

      sectionIds.forEach(id => {
        const section = sectionMap.get(id);
        if (section) {
          sections.push([section]);
        }
      });
    });
  }, [doc]);

  // Reorder lines within a section
  const reorderLines = useCallback((sectionId: string, lineIds: string[]) => {
    const result = findSection(sectionId);
    if (!result) return;

    const lines = result.section.get('lines') as Y.Array<unknown>;
    if (!lines) return;

    const currentLines: Y.Map<unknown>[] = [];
    for (let i = 0; i < lines.length; i++) {
      currentLines.push(lines.get(i) as Y.Map<unknown>);
    }

    const lineMap = new Map<string, Y.Map<unknown>>();
    currentLines.forEach(l => {
      lineMap.set(l.get('id') as string, l);
    });

    doc?.transact(() => {
      while (lines.length > 0) {
        lines.delete(0, 1);
      }

      lineIds.forEach(id => {
        const line = lineMap.get(id);
        if (line) {
          lines.push([line]);
        }
      });
    });
  }, [doc, findSection]);

  // Use initial song while loading
  const effectiveSong = useMemo(() => {
    if (hasSynced && song) {
      return song;
    }
    return initialSong || null;
  }, [hasSynced, song, initialSong]);

  return {
    song: effectiveSong,
    isLoading: !hasSynced && isLoading,
    status,
    error,
    connectedUsers,
    reconnect,
    disconnect,
    doc,
    updateLine,
    addLine,
    deleteLine,
    addSection,
    deleteSection,
    updateSection,
    updateMeta,
    addChord,
    removeChord,
    reorderSections,
    reorderLines,
  };
}
