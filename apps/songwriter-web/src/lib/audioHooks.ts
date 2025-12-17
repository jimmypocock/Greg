/**
 * React Query hooks for audio file operations.
 */

import { useCallback, useState, useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getAudioFiles,
  uploadAudioFile,
  deleteAudioFile,
  updateAudioFile,
  analyzeAudioFile,
  applyAudioAnalysis,
} from './audio';
import { songKeys } from './hooks';
import type { AudioFile, AnalysisStatus, AudioEvent, UpdateAudioFileRequest } from '@/types/audio';

// Query keys
export const audioKeys = {
  all: ['audio'] as const,
  songAudio: (songId: string) => [...audioKeys.all, songId] as const,
  songAudioFiltered: (songId: string, filter: string) => [...audioKeys.all, songId, filter] as const,
  versionAudio: (songId: string, versionId: string) => [...audioKeys.all, songId, 'version', versionId] as const,
};

/**
 * Get audio files for a song (defaults to song-level only).
 */
export function useAudioFiles(songId: string, options?: { sectionVersionId?: string; songLevelOnly?: boolean }) {
  const filterKey = options?.sectionVersionId || (options?.songLevelOnly ? 'song-level' : 'all');
  return useQuery({
    queryKey: audioKeys.songAudioFiltered(songId, filterKey),
    queryFn: () => getAudioFiles(songId, options),
    enabled: !!songId,
  });
}

/**
 * Get audio files for a specific section version.
 */
export function useVersionAudioFiles(songId: string, sectionVersionId: string) {
  return useQuery({
    queryKey: audioKeys.versionAudio(songId, sectionVersionId),
    queryFn: () => getAudioFiles(songId, { sectionVersionId }),
    enabled: !!songId && !!sectionVersionId,
  });
}

/**
 * Upload an audio file, optionally attached to a section version.
 */
export function useUploadAudio(songId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      file,
      isReference,
      sectionVersionId,
    }: {
      file: File;
      isReference?: boolean;
      sectionVersionId?: string;
    }) => uploadAudioFile(songId, file, isReference, sectionVersionId),
    onSuccess: (_, variables) => {
      // Invalidate all audio queries for this song
      queryClient.invalidateQueries({ queryKey: audioKeys.all });
      // Also invalidate the specific version if provided
      if (variables.sectionVersionId) {
        queryClient.invalidateQueries({
          queryKey: audioKeys.versionAudio(songId, variables.sectionVersionId),
        });
      }
    },
  });
}

/**
 * Delete an audio file.
 */
export function useDeleteAudio(songId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (audioId: string) => deleteAudioFile(songId, audioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: audioKeys.songAudio(songId) });
    },
  });
}

/**
 * Update an audio file's metadata.
 */
export function useUpdateAudio(songId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ audioId, data }: { audioId: string; data: UpdateAudioFileRequest }) =>
      updateAudioFile(songId, audioId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: audioKeys.songAudio(songId) });
    },
  });
}

/**
 * Apply analysis results to song.
 */
export function useApplyAudioAnalysis(songId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (audioId: string) => applyAudioAnalysis(songId, audioId),
    onSuccess: () => {
      // Invalidate song to refresh metadata
      queryClient.invalidateQueries({ queryKey: songKeys.detail(songId) });
    },
  });
}

// WebSocket URL for audio analysis
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8081';

interface AnalysisProgress {
  status: 'idle' | 'running' | 'completed' | 'failed';
  stage?: string;
  progress?: number;
  message?: string;
  result?: {
    tempo: number | null;
    tempo_confidence: number | null;
    key: string | null;
    key_confidence: number | null;
    duration_seconds: number | null;
  };
  error?: string;
}

/**
 * Hook for running audio analysis with WebSocket progress updates.
 */
export function useAnalyzeAudio(songId: string) {
  const queryClient = useQueryClient();
  const [audioFileId, setAudioFileId] = useState<string | null>(null);
  const [progress, setProgress] = useState<AnalysisProgress>({ status: 'idle' });
  const wsRef = useRef<WebSocket | null>(null);

  // Clean up WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  const startAnalysis = useCallback(
    async (targetAudioFileId: string) => {
      // Reset state
      setAudioFileId(targetAudioFileId);
      setProgress({ status: 'running', message: 'Starting analysis...' });

      // Close existing WebSocket
      if (wsRef.current) {
        wsRef.current.close();
      }

      try {
        // Start the analysis task
        const response = await analyzeAudioFile(songId, targetAudioFileId);
        const taskId = response.task_id;

        // Connect to WebSocket for progress
        const ws = new WebSocket(`${WS_BASE_URL}/ws/jobs/${taskId}`);
        wsRef.current = ws;

        ws.onmessage = (event) => {
          try {
            const data: AudioEvent = JSON.parse(event.data);

            switch (data.event) {
              case 'audio.started':
                setProgress({
                  status: 'running',
                  message: data.data.message || 'Starting analysis...',
                });
                break;

              case 'audio.analyzing':
                setProgress({
                  status: 'running',
                  stage: data.data.stage,
                  progress: data.data.progress,
                  message: data.data.message || 'Analyzing...',
                });
                break;

              case 'audio.completed':
                setProgress({
                  status: 'completed',
                  result: {
                    tempo: data.data.tempo ?? null,
                    tempo_confidence: data.data.tempo_confidence ?? null,
                    key: data.data.key ?? null,
                    key_confidence: data.data.key_confidence ?? null,
                    duration_seconds: data.data.duration_seconds ?? null,
                  },
                });
                // Refresh audio files to get updated status
                queryClient.invalidateQueries({ queryKey: audioKeys.songAudio(songId) });
                ws.close();
                break;

              case 'audio.failed':
                setProgress({
                  status: 'failed',
                  error: data.data.error || 'Analysis failed',
                });
                queryClient.invalidateQueries({ queryKey: audioKeys.songAudio(songId) });
                ws.close();
                break;
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err);
          }
        };

        ws.onerror = () => {
          setProgress({
            status: 'failed',
            error: 'WebSocket connection error',
          });
        };

        ws.onclose = () => {
          wsRef.current = null;
        };
      } catch (err) {
        setProgress({
          status: 'failed',
          error: err instanceof Error ? err.message : 'Failed to start analysis',
        });
      }
    },
    [songId, queryClient]
  );

  const reset = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setAudioFileId(null);
    setProgress({ status: 'idle' });
  }, []);

  return {
    audioFileId,
    progress,
    startAnalysis,
    reset,
    isAnalyzing: progress.status === 'running',
    isComplete: progress.status === 'completed',
    isFailed: progress.status === 'failed',
  };
}
