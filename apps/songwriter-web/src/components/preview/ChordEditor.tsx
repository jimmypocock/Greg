'use client';

import { useState, useRef, useEffect } from 'react';

interface ChordEditorProps {
  /** Initial chord value (for editing existing chord) */
  initialChord?: string;
  /** Position in the DOM for the popover */
  anchorPosition: { x: number; y: number };
  /** Called when chord is saved */
  onSave: (chord: string) => void | Promise<void>;
  /** Called when chord is deleted (only shown if editing existing) */
  onDelete?: () => void | Promise<void>;
  /** Called when editor is closed without saving */
  onClose: () => void;
}

export function ChordEditor({
  initialChord = '',
  anchorPosition,
  onSave,
  onDelete,
  onClose,
}: ChordEditorProps) {
  const [chord, setChord] = useState(initialChord);
  const [isSaving, setIsSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  // Close on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        if (!isSaving) {
          onClose();
        }
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose, isSaving]);

  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (isSaving) return;

    if (e.key === 'Enter') {
      e.preventDefault();
      if (chord.trim()) {
        await handleSave();
      } else if (onDelete) {
        // Empty chord = delete
        await handleDelete();
      } else {
        onClose();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  const handleSave = async () => {
    if (chord.trim() && !isSaving) {
      setIsSaving(true);
      try {
        await onSave(chord.trim());
      } finally {
        setIsSaving(false);
      }
    } else if (!chord.trim()) {
      onClose();
    }
  };

  const handleDelete = async () => {
    if (onDelete && !isSaving) {
      setIsSaving(true);
      try {
        await onDelete();
      } finally {
        setIsSaving(false);
      }
    }
  };

  return (
    <div
      ref={popoverRef}
      className="fixed z-50 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 p-2"
      style={{
        left: anchorPosition.x,
        top: anchorPosition.y,
        transform: 'translate(-50%, -100%) translateY(-8px)',
      }}
    >
      <div className="flex items-center gap-2">
        <input
          ref={inputRef}
          type="text"
          value={chord}
          onChange={(e) => setChord(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Am, G7, Cmaj7..."
          disabled={isSaving}
          className="
            w-24 px-2 py-1 text-sm
            bg-gray-50 dark:bg-gray-900
            border border-gray-300 dark:border-gray-600
            rounded
            focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
            placeholder-gray-400
            disabled:opacity-50
          "
        />
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30 rounded disabled:opacity-50"
          title="Save chord"
        >
          {isSaving ? (
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </button>
        {onDelete && (
          <button
            onClick={handleDelete}
            disabled={isSaving}
            className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded disabled:opacity-50"
            title="Delete chord"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
      <div className="mt-1 text-xs text-gray-400 text-center">
        Enter to save · Esc to cancel
      </div>
    </div>
  );
}
