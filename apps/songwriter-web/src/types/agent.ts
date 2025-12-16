/**
 * Agent-related types for the Songwriter app.
 */

export enum AgentType {
  CRITIC = 'critic',
  LYRICIST = 'lyricist',
  STRUCTURE = 'structure',
  MELODY = 'melody',
}

export enum AgentTaskType {
  FULL_REVIEW = 'full_review',
  SECTION_REVIEW = 'section_review',
  CHECK_CLICHES = 'check_cliches',
  ANALYZE_RHYTHM = 'analyze_rhythm',
  STRUCTURE_ANALYSIS = 'structure_analysis',
}

// Response when starting an agent task (returns immediately)
export interface AgentTaskResponse {
  task_id: string;
  song_id: string;
  song_title: string;
  task_type: string;
  message: string;
  websocket_url: string;
}

// Task status response (for polling)
export interface TaskStatusResponse {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress?: {
    stage: string;
    percent: number;
    message: string;
    details?: Record<string, unknown>;
  };
  result?: AgentTaskResult;
  error?: string;
}

// Final result from a completed agent task
export interface AgentTaskResult {
  success: boolean;
  result: string;
  duration_ms: number;
  input_tokens: number;
  output_tokens: number;
  total_cost_usd: string;
}

// WebSocket event types
export type AgentEventType =
  | 'agent.started'
  | 'agent.thinking'
  | 'agent.chunk'
  | 'agent.tool.start'
  | 'agent.tool.end'
  | 'agent.step.completed'
  | 'agent.completed'
  | 'agent.failed';

export interface AgentEvent {
  event: AgentEventType;
  data: AgentEventData;
  timestamp: string;
}

export interface AgentEventData {
  task_id: string;
  agent_name?: string;
  task_description?: string;
  task_type?: string;
  song_title?: string;
  thought?: string;
  text?: string;  // Streaming text chunk
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: string;
  result?: string;
  duration_ms?: number;
  error?: string;
}

// Legacy response type (for backwards compatibility with review history)
export interface AgentResponse {
  success: boolean;
  song_id: string;
  song_title: string;
  task: string;
  result: string;
  review_id?: string;
  input_tokens: number;
  output_tokens: number;
  total_cost_usd: string;
  duration_ms: number;
  model?: string;
}

export interface ReviewHistoryItem {
  id: string;
  agent_type: AgentType;
  task_type: AgentTaskType;
  result: string;
  input_tokens: number;
  output_tokens: number;
  total_cost_usd: string;
  duration_ms?: number;
  model?: string;
  created_at: string;
}

export interface ReviewHistoryResponse {
  song_id: string;
  reviews: ReviewHistoryItem[];
  total_cost_usd: string;
}

export interface ReviewRequest {
  llm?: string;
}

export interface SectionReviewRequest {
  section_index: number;
  llm?: string;
}
