'use client';

import { useState, useRef } from 'react';
import { useDeleteAudio } from '@/hooks/queries/audio';
import type { AudioFile } from '@/types/audio';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';

interface VersionAudioItemProps {
  audioFile: AudioFile;
  songId: string;
  compact?: boolean;
}

export function VersionAudioItem({ audioFile, songId, compact = false }: VersionAudioItemProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const deleteAudio = useDeleteAudio(songId);
  const [showConfirm, setShowConfirm] = useState(false);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleDelete = async () => {
    await deleteAudio.mutateAsync(audioFile.id);
    setShowConfirm(false);
  };

  return (
    <div className={`flex items-center gap-2 ${compact ? 'py-1 px-1.5' : 'py-1.5 px-2'} bg-gray-50 dark:bg-gray-750 rounded text-xs`}>
      <audio
        ref={audioRef}
        src={`${API_BASE_URL}/songs/${songId}/audio/${audioFile.id}/stream`}
        preload="metadata"
        onEnded={() => setIsPlaying(false)}
      />
      <button
        onClick={togglePlay}
        className={`flex-shrink-0 ${compact ? 'w-5 h-5' : 'w-6 h-6'} flex items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-200`}
      >
        {isPlaying ? (
          <svg className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
          </svg>
        ) : (
          <svg className={`${compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} ml-0.5`} fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>
      <span className="flex-1 truncate text-gray-600 dark:text-gray-300" title={audioFile.filename}>
        {audioFile.display_name || audioFile.filename}
      </span>
      {showConfirm ? (
        <div className="flex items-center gap-1">
          <button
            onClick={handleDelete}
            disabled={deleteAudio.isPending}
            className="px-1.5 py-0.5 text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
          >
            {deleteAudio.isPending ? '...' : 'Delete'}
          </button>
          <button
            onClick={() => setShowConfirm(false)}
            className="px-1.5 py-0.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setShowConfirm(true)}
          className="p-1 text-gray-400 hover:text-red-500"
          title="Delete"
        >
          <svg className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}

interface AudioUploadButtonProps {
  onUpload: (file: File) => void;
  isUploading?: boolean;
  compact?: boolean;
}

export function AudioUploadButton({ onUpload, isUploading, compact = false }: AudioUploadButtonProps) {
  return (
    <label
      className={`
        flex items-center justify-center gap-1 ${compact ? 'px-1.5 py-1 text-[10px]' : 'px-2 py-1.5 text-xs'}
        text-gray-500 dark:text-gray-400
        hover:bg-gray-100 dark:hover:bg-gray-700
        border border-dashed border-gray-300 dark:border-gray-600
        rounded cursor-pointer transition-colors
        ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
      `}
      title="Upload audio snippet for this version"
    >
      <input
        type="file"
        accept="audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/x-m4a,audio/mp4"
        className="hidden"
        disabled={isUploading}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            onUpload(file);
            e.target.value = '';
          }
        }}
        onClick={(e) => e.stopPropagation()}
      />
      {isUploading ? (
        <svg className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25 animate-spin" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : (
        <svg className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
        </svg>
      )}
      <span>Upload Audio</span>
    </label>
  );
}
