/**
 * React Query hooks for agent interactions.
 *
 * Agent tasks now return immediately with a task_id.
 * Use useAgentTask hook for the full async workflow with WebSocket updates.
 */

import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  reviewSong,
  reviewSection,
  checkCliches,
  analyzeRhythm,
  getReviewHistory,
  getTaskStatus,
} from '@/lib/agents';
import { useAgentWebSocket, type AgentProgress } from '@/hooks/useAgentWebSocket';
import type {
  AgentTaskResponse,
  AgentTaskResult,
  AgentType,
  ReviewRequest,
  SectionReviewRequest,
} from '@/types/agent';

// Query keys
export const agentKeys = {
  all: ['agents'] as const,
  reviews: () => [...agentKeys.all, 'reviews'] as const,
  songReviews: (songId: string) => [...agentKeys.reviews(), songId] as const,
  taskStatus: (taskId: string) => [...agentKeys.all, 'task', taskId] as const,
};

// Get review history for a song
export function useReviewHistory(
  songId: string,
  agentType?: AgentType,
  limit?: number
) {
  return useQuery({
    queryKey: [...agentKeys.songReviews(songId), { agentType, limit }],
    queryFn: () => getReviewHistory(songId, agentType, limit),
    enabled: !!songId,
  });
}

// Get task status (for polling fallback)
export function useTaskStatus(taskId: string | null) {
  return useQuery({
    queryKey: agentKeys.taskStatus(taskId || ''),
    queryFn: () => getTaskStatus(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Stop polling when task is done
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        return false;
      }
      return 2000; // Poll every 2 seconds while running
    },
  });
}

// Start full song review
export function useStartReviewSong(songId: string) {
  return useMutation({
    mutationFn: (options?: ReviewRequest) => reviewSong(songId, options),
  });
}

// Start section review
export function useStartReviewSection(songId: string) {
  return useMutation({
    mutationFn: (options: SectionReviewRequest) => reviewSection(songId, options),
  });
}

// Start cliche check
export function useStartCheckCliches(songId: string) {
  return useMutation({
    mutationFn: (options?: ReviewRequest) => checkCliches(songId, options),
  });
}

// Start rhythm analysis
export function useStartAnalyzeRhythm(songId: string) {
  return useMutation({
    mutationFn: (options?: ReviewRequest) => analyzeRhythm(songId, options),
  });
}

/**
 * Combined hook for running agent tasks with WebSocket progress updates.
 *
 * Handles the full workflow:
 * 1. Start the task (returns task_id immediately)
 * 2. Connect to WebSocket for real-time updates
 * 3. Track progress and final result
 */
export function useAgentTask(songId: string) {
  const queryClient = useQueryClient();
  const [taskResponse, setTaskResponse] = useState<AgentTaskResponse | null>(null);
  const [finalResult, setFinalResult] = useState<AgentTaskResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleComplete = useCallback(
    (result: AgentTaskResult) => {
      setFinalResult(result);
      // Invalidate review history to show new review
      queryClient.invalidateQueries({ queryKey: agentKeys.songReviews(songId) });
    },
    [queryClient, songId]
  );

  const handleError = useCallback((err: string) => {
    setError(err);
  }, []);

  const websocket = useAgentWebSocket({
    onComplete: handleComplete,
    onError: handleError,
  });

  const startReview = useStartReviewSong(songId);
  const startCheckCliches = useStartCheckCliches(songId);
  const startAnalyzeRhythm = useStartAnalyzeRhythm(songId);

  const runTask = useCallback(
    async (
      taskType: 'full' | 'cliches' | 'rhythm',
      options?: ReviewRequest
    ) => {
      // Reset state
      setTaskResponse(null);
      setFinalResult(null);
      setError(null);
      websocket.reset();

      try {
        let response: AgentTaskResponse;
        switch (taskType) {
          case 'full':
            response = await startReview.mutateAsync(options);
            break;
          case 'cliches':
            response = await startCheckCliches.mutateAsync(options);
            break;
          case 'rhythm':
            response = await startAnalyzeRhythm.mutateAsync(options);
            break;
        }

        setTaskResponse(response);
        // Connect to WebSocket for real-time updates
        websocket.connect(response.task_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start task');
      }
    },
    [startReview, startCheckCliches, startAnalyzeRhythm, websocket]
  );

  const reset = useCallback(() => {
    setTaskResponse(null);
    setFinalResult(null);
    setError(null);
    websocket.reset();
  }, [websocket]);

  return {
    // Task state
    taskResponse,
    progress: websocket.progress,
    finalResult,
    error,
    // Status helpers
    isStarting: startReview.isPending || startCheckCliches.isPending || startAnalyzeRhythm.isPending,
    isRunning: websocket.progress.status === 'running',
    isComplete: websocket.progress.status === 'completed',
    isFailed: websocket.progress.status === 'failed',
    // Actions
    runTask,
    reset,
  };
}

// Legacy hooks for backwards compatibility
export function useReviewSong(songId: string) {
  return useStartReviewSong(songId);
}

export function useReviewSection(songId: string) {
  return useStartReviewSection(songId);
}

export function useCheckCliches(songId: string) {
  return useStartCheckCliches(songId);
}

export function useAnalyzeRhythm(songId: string) {
  return useStartAnalyzeRhythm(songId);
}
