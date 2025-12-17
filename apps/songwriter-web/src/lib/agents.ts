/**
 * Agent API functions for the Songwriter app.
 *
 * All agent task endpoints now return immediately with a task_id.
 * Connect to WebSocket at /ws/jobs/{task_id} for real-time progress updates.
 */

import { get, post } from './api';
import type {
  AgentTaskResponse,
  AgentType,
  ChatRequest,
  ReviewHistoryResponse,
  ReviewRequest,
  SectionReviewRequest,
  TaskStatusResponse,
} from '@/types/agent';

/**
 * Start a full song review from the Critic agent.
 * Returns immediately with a task_id for tracking progress via WebSocket.
 */
export async function reviewSong(
  songId: string,
  options: ReviewRequest = {}
): Promise<AgentTaskResponse> {
  return post<AgentTaskResponse, ReviewRequest>(`/agents/${songId}/review`, options);
}

/**
 * Start a review of a specific section.
 * Returns immediately with a task_id for tracking progress via WebSocket.
 */
export async function reviewSection(
  songId: string,
  options: SectionReviewRequest
): Promise<AgentTaskResponse> {
  return post<AgentTaskResponse, SectionReviewRequest>(
    `/agents/${songId}/review-section`,
    options
  );
}

/**
 * Start a cliche scan on the song.
 * Returns immediately with a task_id for tracking progress via WebSocket.
 */
export async function checkCliches(
  songId: string,
  options: ReviewRequest = {}
): Promise<AgentTaskResponse> {
  return post<AgentTaskResponse, ReviewRequest>(
    `/agents/${songId}/check-cliches`,
    options
  );
}

/**
 * Start rhythm analysis on the song.
 * Returns immediately with a task_id for tracking progress via WebSocket.
 */
export async function analyzeRhythm(
  songId: string,
  options: ReviewRequest = {}
): Promise<AgentTaskResponse> {
  return post<AgentTaskResponse, ReviewRequest>(
    `/agents/${songId}/analyze-rhythm`,
    options
  );
}

/**
 * Get the status of an agent task.
 * Use this for polling if WebSocket is not available.
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  return get<TaskStatusResponse>(`/agents/tasks/${taskId}`);
}

/**
 * Start a conversational chat session about a song.
 * Returns immediately with a task_id for tracking progress via WebSocket.
 *
 * The AI assistant helps with songwriting while staying focused on the song.
 * Conversation history is limited to 20 messages.
 */
export async function chatWithSong(
  songId: string,
  message: string,
  conversationHistory: Array<{ role: 'user' | 'assistant'; content: string }> = [],
  options: { llm?: string } = {}
): Promise<AgentTaskResponse> {
  const request: ChatRequest = {
    message,
    conversation_history: conversationHistory,
    llm: options.llm,
  };
  return post<AgentTaskResponse, ChatRequest>(`/agents/${songId}/chat`, request);
}

/**
 * Get review history for a song.
 */
export async function getReviewHistory(
  songId: string,
  agentType?: AgentType,
  limit?: number
): Promise<ReviewHistoryResponse> {
  let path = `/agents/${songId}/reviews`;
  const params = new URLSearchParams();
  if (agentType) params.set('agent_type', agentType);
  if (limit) params.set('limit', limit.toString());
  const queryString = params.toString();
  if (queryString) path += `?${queryString}`;
  return get<ReviewHistoryResponse>(path);
}
