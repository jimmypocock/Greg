'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Song, SongUpdateRequest } from '@/types';

interface SongNotesProps {
  song: Song;
  onUpdate: (data: SongUpdateRequest) => Promise<void>;
}

export function SongNotes({ song, onUpdate }: SongNotesProps) {
  const [notes, setNotes] = useState(song.notes || '');
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastSavedValueRef = useRef(song.notes || '');

  // Sync with song prop when it changes externally
  useEffect(() => {
    if (song.notes !== lastSavedValueRef.current) {
      setNotes(song.notes || '');
      lastSavedValueRef.current = song.notes || '';
    }
  }, [song.notes]);

  // Debounced save function
  const saveNotes = useCallback(async (value: string) => {
    if (value === lastSavedValueRef.current) return;

    setIsSaving(true);
    try {
      await onUpdate({ notes: value });
      lastSavedValueRef.current = value;
      setLastSaved(new Date());
    } catch (error) {
      console.error('Failed to save notes:', error);
    } finally {
      setIsSaving(false);
    }
  }, [onUpdate]);

  // Handle text change with debounced auto-save
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setNotes(value);

    // Clear existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Set new timeout for auto-save (500ms debounce)
    saveTimeoutRef.current = setTimeout(() => {
      saveNotes(value);
    }, 500);
  };

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // Save on blur if there are unsaved changes
  const handleBlur = () => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    if (notes !== lastSavedValueRef.current) {
      saveNotes(notes);
    }
  };

  return (
    <div className="space-y-2">
      <textarea
        value={notes}
        onChange={handleChange}
        onBlur={handleBlur}
        placeholder="Jot down themes, word ideas, inspirations, references, or anything else about your song..."
        className="w-full h-48 px-3 py-2 text-sm border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-y"
      />
      <div className="flex items-center justify-end text-xs text-gray-400 dark:text-gray-500">
        {isSaving ? (
          <span className="flex items-center gap-1">
            <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Saving...
          </span>
        ) : lastSaved ? (
          <span>Auto-saved</span>
        ) : null}
      </div>
    </div>
  );
}
