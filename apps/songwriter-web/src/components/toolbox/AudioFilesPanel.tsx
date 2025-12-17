'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import {
  useAudioFiles,
  useUploadAudio,
  useDeleteAudio,
  useUpdateAudio,
  useAnalyzeAudio,
  useApplyAudioAnalysis,
} from '@/lib/audioHooks';
import { AnalysisStatus, type AudioFile } from '@/types/audio';

interface AudioFilesPanelProps {
  songId: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '--';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

interface AudioPlayerProps {
  songId: string;
  audioId: string;
  duration: number | null;
}

function AudioPlayer({ songId, audioId, duration }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [audioDuration, setAudioDuration] = useState(duration || 0);
  const [isLoading, setIsLoading] = useState(false);

  // Construct audio URL - we need to serve the file through the API
  const audioUrl = `${API_BASE_URL}/songs/${songId}/audio/${audioId}/stream`;

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleDurationChange = () => setAudioDuration(audio.duration || duration || 0);
    const handleEnded = () => setIsPlaying(false);
    const handleLoadStart = () => setIsLoading(true);
    const handleCanPlay = () => setIsLoading(false);
    const handleError = () => setIsLoading(false);

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('loadstart', handleLoadStart);
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener('error', handleError);
    };
  }, [duration]);

  const togglePlayPause = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    const progressBar = progressRef.current;
    if (!audio || !progressBar || !audioDuration) return;

    const rect = progressBar.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percentage = clickX / rect.width;
    const newTime = percentage * audioDuration;

    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const progress = audioDuration > 0 ? (currentTime / audioDuration) * 100 : 0;

  return (
    <div className="flex items-center gap-2 py-2">
      <audio ref={audioRef} src={audioUrl} preload="metadata" />

      {/* Play/Pause button */}
      <button
        onClick={togglePlayPause}
        disabled={isLoading}
        className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-200 dark:hover:bg-indigo-900 transition-colors disabled:opacity-50"
      >
        {isLoading ? (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : isPlaying ? (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
          </svg>
        ) : (
          <svg className="w-4 h-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
      </button>

      {/* Progress bar */}
      <div className="flex-1 flex items-center gap-2">
        <span className="text-xs text-gray-500 dark:text-gray-400 w-10 text-right tabular-nums">
          {formatTime(currentTime)}
        </span>
        <div
          ref={progressRef}
          onClick={handleProgressClick}
          className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full cursor-pointer overflow-hidden group"
        >
          <div
            className="h-full bg-indigo-500 dark:bg-indigo-400 rounded-full transition-all duration-100 group-hover:bg-indigo-600 dark:group-hover:bg-indigo-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 w-10 tabular-nums">
          {formatTime(audioDuration)}
        </span>
      </div>
    </div>
  );
}

function AudioFileItem({
  audioFile,
  songId,
  onAnalyze,
  isAnalyzing,
}: {
  audioFile: AudioFile;
  songId: string;
  onAnalyze: (id: string) => void;
  isAnalyzing: boolean;
}) {
  const deleteAudio = useDeleteAudio(songId);
  const updateAudio = useUpdateAudio(songId);
  const applyAnalysis = useApplyAudioAnalysis(songId);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState(audioFile.display_name || '');
  const nameInputRef = useRef<HTMLInputElement>(null);

  // Focus input when entering edit mode
  useEffect(() => {
    if (isEditingName && nameInputRef.current) {
      nameInputRef.current.focus();
      nameInputRef.current.select();
    }
  }, [isEditingName]);

  const handleDelete = async () => {
    await deleteAudio.mutateAsync(audioFile.id);
    setShowConfirmDelete(false);
  };

  const handleApply = async () => {
    await applyAnalysis.mutateAsync(audioFile.id);
  };

  const handleNameClick = () => {
    setEditedName(audioFile.display_name || audioFile.filename);
    setIsEditingName(true);
  };

  const handleNameSave = async () => {
    const trimmedName = editedName.trim();
    // If empty or same as filename, set to null (remove display name)
    const newDisplayName = trimmedName && trimmedName !== audioFile.filename ? trimmedName : '';

    if (newDisplayName !== (audioFile.display_name || '')) {
      await updateAudio.mutateAsync({
        audioId: audioFile.id,
        data: { display_name: newDisplayName || undefined },
      });
    }
    setIsEditingName(false);
  };

  const handleNameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleNameSave();
    } else if (e.key === 'Escape') {
      setIsEditingName(false);
      setEditedName(audioFile.display_name || '');
    }
  };

  const displayName = audioFile.display_name || audioFile.filename;

  const canAnalyze = audioFile.analysis_status === AnalysisStatus.PENDING ||
    audioFile.analysis_status === AnalysisStatus.FAILED;
  const canApply = audioFile.analysis_status === AnalysisStatus.COMPLETED &&
    (audioFile.detected_tempo || audioFile.detected_key);

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-2">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <svg className="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
          {isEditingName ? (
            <input
              ref={nameInputRef}
              type="text"
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
              onBlur={handleNameSave}
              onKeyDown={handleNameKeyDown}
              className="flex-1 min-w-0 text-sm font-medium bg-white dark:bg-gray-800 border border-indigo-500 rounded px-2 py-0.5 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              placeholder={audioFile.filename}
            />
          ) : (
            <button
              onClick={handleNameClick}
              className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors text-left"
              title="Click to edit name"
            >
              {displayName}
            </button>
          )}
          {audioFile.is_reference && (
            <span className="px-1.5 py-0.5 text-xs bg-indigo-100 text-indigo-600 dark:bg-indigo-900 dark:text-indigo-300 rounded flex-shrink-0">
              Reference
            </span>
          )}
        </div>
      </div>

      {/* Audio Player */}
      <AudioPlayer
        songId={songId}
        audioId={audioFile.id}
        duration={audioFile.duration_seconds}
      />

      {/* File info */}
      <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
        <span>{formatFileSize(audioFile.file_size_bytes)}</span>
        {audioFile.display_name && (
          <span className="truncate" title={audioFile.filename}>
            {audioFile.filename}
          </span>
        )}
      </div>

      {/* Analysis results */}
      {audioFile.analysis_status === AnalysisStatus.COMPLETED && (
        <div className="space-y-1">
          {/* Primary analysis: Tempo, Key, Time Signature */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            {audioFile.detected_tempo && (
              <div className="flex items-center gap-1">
                <span className="text-gray-500 dark:text-gray-400">Tempo:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {Math.round(audioFile.detected_tempo)} BPM
                </span>
                {audioFile.confidence_tempo && (
                  <span className="text-xs text-gray-400">
                    ({Math.round(audioFile.confidence_tempo * 100)}%)
                  </span>
                )}
              </div>
            )}
            {audioFile.detected_key && (
              <div className="flex items-center gap-1">
                <span className="text-gray-500 dark:text-gray-400">Key:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {audioFile.detected_key}
                </span>
                {audioFile.confidence_key && (
                  <span className="text-xs text-gray-400">
                    ({Math.round(audioFile.confidence_key * 100)}%)
                  </span>
                )}
              </div>
            )}
            {audioFile.detected_time_signature && (
              <div className="flex items-center gap-1">
                <span className="text-gray-500 dark:text-gray-400">Time:</span>
                <span className="font-medium text-gray-900 dark:text-gray-100">
                  {audioFile.detected_time_signature}
                </span>
                {audioFile.confidence_time_signature && (
                  <span className="text-xs text-gray-400">
                    ({Math.round(audioFile.confidence_time_signature * 100)}%)
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Extended analysis: Chords and Beats */}
          {(audioFile.detected_chords?.length || audioFile.beat_positions?.length) && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
              {audioFile.detected_chords && audioFile.detected_chords.length > 0 && (
                <span>
                  {audioFile.detected_chords.length} chord{audioFile.detected_chords.length !== 1 ? 's' : ''} detected
                </span>
              )}
              {audioFile.beat_positions && audioFile.beat_positions.length > 0 && (
                <span>
                  {audioFile.beat_positions.length} beats
                </span>
              )}
            </div>
          )}

          {/* Show first few chords as a preview */}
          {audioFile.detected_chords && audioFile.detected_chords.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {audioFile.detected_chords.slice(0, 8).map((chord, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 text-xs font-mono bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
                  title={`${chord.start.toFixed(1)}s - ${chord.end.toFixed(1)}s`}
                >
                  {chord.chord}
                </span>
              ))}
              {audioFile.detected_chords.length > 8 && (
                <span className="px-1.5 py-0.5 text-xs text-gray-400">
                  +{audioFile.detected_chords.length - 8} more
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Error message */}
      {audioFile.analysis_status === AnalysisStatus.FAILED && audioFile.analysis_error && (
        <p className="text-xs text-red-600 dark:text-red-400">{audioFile.analysis_error}</p>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-1">
        {canAnalyze && (
          <button
            onClick={() => onAnalyze(audioFile.id)}
            disabled={isAnalyzing}
            className="px-2 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAnalyzing ? 'Analyzing...' : 'Analyze'}
          </button>
        )}
        {canApply && (
          <button
            onClick={handleApply}
            disabled={applyAnalysis.isPending}
            className="px-2 py-1 text-xs font-medium text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/30 rounded disabled:opacity-50"
          >
            {applyAnalysis.isPending ? 'Applying...' : 'Apply to Song'}
          </button>
        )}
        <div className="flex-1" />
        {showConfirmDelete ? (
          <>
            <button
              onClick={handleDelete}
              disabled={deleteAudio.isPending}
              className="px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
            >
              {deleteAudio.isPending ? 'Deleting...' : 'Confirm'}
            </button>
            <button
              onClick={() => setShowConfirmDelete(false)}
              className="px-2 py-1 text-xs font-medium text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            onClick={() => setShowConfirmDelete(true)}
            className="p-1 text-gray-400 hover:text-red-500 rounded"
            title="Delete"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}

export function AudioFilesPanel({ songId }: AudioFilesPanelProps) {
  // Only show song-level audio files (not attached to any version)
  const { data, isLoading, error } = useAudioFiles(songId, { songLevelOnly: true });
  const uploadAudio = useUploadAudio(songId);
  const analyzeAudio = useAnalyzeAudio(songId);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0];
    await uploadAudio.mutateAsync({ file, isReference: false });

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [uploadAudio]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleAnalyze = useCallback((audioId: string) => {
    analyzeAudio.startAnalysis(audioId);
  }, [analyzeAudio]);

  if (isLoading) {
    return (
      <div className="space-y-2">
        <div className="h-20 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-3 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg">
        Failed to load audio files
      </div>
    );
  }

  const audioFiles = data?.audio_files || [];

  return (
    <div className="space-y-3">
      {/* Upload area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer
          ${isDragging
            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
            : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
          }
        `}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/mpeg,audio/mp3,audio/wav,audio/x-wav,audio/x-m4a,audio/mp4"
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files)}
        />
        {uploadAudio.isPending ? (
          <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Uploading...
          </div>
        ) : (
          <>
            <svg className="w-8 h-8 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              {isDragging ? 'Drop audio file here' : 'Click or drag audio file (mp3, wav, m4a)'}
            </p>
          </>
        )}
      </div>

      {/* Analysis progress */}
      {analyzeAudio.isAnalyzing && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>{analyzeAudio.progress.message || 'Analyzing audio...'}</span>
          </div>
        </div>
      )}

      {/* Audio files list */}
      {audioFiles.length === 0 ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
          No audio files yet. Upload an mp3, wav, or m4a file to detect tempo and key.
        </p>
      ) : (
        <div className="space-y-2">
          {audioFiles.map((audioFile) => (
            <AudioFileItem
              key={audioFile.id}
              audioFile={audioFile}
              songId={songId}
              onAnalyze={handleAnalyze}
              isAnalyzing={analyzeAudio.isAnalyzing && analyzeAudio.audioFileId === audioFile.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}
