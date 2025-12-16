'use client';

import { useState } from 'react';
import { Song, SongStatus, SongUpdateRequest } from '@/types';

interface MetadataEditorProps {
  song: Song;
  onUpdate: (data: SongUpdateRequest) => Promise<void>;
  isUpdating?: boolean;
}

const statusOptions: { value: SongStatus; label: string; color: string }[] = [
  { value: SongStatus.IDEA, label: 'Idea', color: 'bg-gray-100 text-gray-700' },
  { value: SongStatus.DRAFT, label: 'Draft', color: 'bg-yellow-100 text-yellow-700' },
  { value: SongStatus.IN_PROGRESS, label: 'In Progress', color: 'bg-blue-100 text-blue-700' },
  { value: SongStatus.REVIEW, label: 'Review', color: 'bg-purple-100 text-purple-700' },
  { value: SongStatus.FINISHED, label: 'Finished', color: 'bg-green-100 text-green-700' },
];

export function MetadataEditor({ song, onUpdate, isUpdating }: MetadataEditorProps) {
  const [title, setTitle] = useState(song.title);
  const [key, setKey] = useState(song.key || '');
  const [tempo, setTempo] = useState(song.tempo?.toString() || '');
  const [feel, setFeel] = useState(song.feel || '');
  const [hasChanges, setHasChanges] = useState(false);

  const handleTitleChange = (value: string) => {
    setTitle(value);
    setHasChanges(true);
  };

  const handleSave = async () => {
    await onUpdate({
      title: title !== song.title ? title : undefined,
      key: key !== (song.key || '') ? key || undefined : undefined,
      tempo: tempo !== (song.tempo?.toString() || '') ? (tempo ? parseInt(tempo, 10) : undefined) : undefined,
      feel: feel !== (song.feel || '') ? feel || undefined : undefined,
    });
    setHasChanges(false);
  };

  const handleStatusChange = async (status: SongStatus) => {
    await onUpdate({ status });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && hasChanges) {
      handleSave();
    }
  };

  return (
    <div className="space-y-4">
      {/* Title */}
      <div>
        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
          Title
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => handleTitleChange(e.target.value)}
          onBlur={() => hasChanges && handleSave()}
          onKeyDown={handleKeyDown}
          className="
            w-full px-3 py-2 text-sm
            bg-gray-50 dark:bg-gray-800
            border border-gray-200 dark:border-gray-600
            rounded-lg
            focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
            text-gray-900 dark:text-gray-100
          "
        />
      </div>

      {/* Key and Tempo in a row */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            Key
          </label>
          <input
            type="text"
            value={key}
            onChange={(e) => { setKey(e.target.value); setHasChanges(true); }}
            onBlur={() => hasChanges && handleSave()}
            onKeyDown={handleKeyDown}
            placeholder="G"
            className="
              w-full px-3 py-2 text-sm
              bg-gray-50 dark:bg-gray-800
              border border-gray-200 dark:border-gray-600
              rounded-lg
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
              text-gray-900 dark:text-gray-100
            "
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
            BPM
          </label>
          <input
            type="number"
            value={tempo}
            onChange={(e) => { setTempo(e.target.value); setHasChanges(true); }}
            onBlur={() => hasChanges && handleSave()}
            onKeyDown={handleKeyDown}
            placeholder="120"
            className="
              w-full px-3 py-2 text-sm
              bg-gray-50 dark:bg-gray-800
              border border-gray-200 dark:border-gray-600
              rounded-lg
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
              text-gray-900 dark:text-gray-100
            "
          />
        </div>
      </div>

      {/* Feel */}
      <div>
        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
          Feel / Mood
        </label>
        <input
          type="text"
          value={feel}
          onChange={(e) => { setFeel(e.target.value); setHasChanges(true); }}
          onBlur={() => hasChanges && handleSave()}
          onKeyDown={handleKeyDown}
          placeholder="Upbeat, melancholic, driving..."
          className="
            w-full px-3 py-2 text-sm
            bg-gray-50 dark:bg-gray-800
            border border-gray-200 dark:border-gray-600
            rounded-lg
            focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
            text-gray-900 dark:text-gray-100
          "
        />
      </div>

      {/* Status */}
      <div>
        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
          Status
        </label>
        <div className="flex flex-wrap gap-2">
          {statusOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => handleStatusChange(option.value)}
              disabled={isUpdating}
              className={`
                px-3 py-1.5 text-xs font-medium rounded-full
                transition-all duration-150
                ${song.status === option.value
                  ? `${option.color} ring-2 ring-offset-1 ring-indigo-500`
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }
                disabled:opacity-50
              `}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {/* Time Signature (read-only for now) */}
      {song.time_signature && song.time_signature !== '4/4' && (
        <div className="text-xs text-gray-500 dark:text-gray-400">
          Time: {song.time_signature}
        </div>
      )}
    </div>
  );
}
