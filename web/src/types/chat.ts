/**
 * Chat-related types for the AI Orchestrator panel.
 */

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  taskId?: string;
  metadata?: ChatMessageMetadata;
}

export interface ChatMessageMetadata {
  taskType?: string;
  duration_ms?: number;
  tokens?: {
    input: number;
    output: number;
  };
  cost?: string;
  toolsUsed?: string[];
}

export interface ChatSession {
  messages: ChatMessage[];
  isProcessing: boolean;
  currentTaskId: string | null;
}

export type QuickActionType =
  | 'full_review'
  | 'check_cliches'
  | 'analyze_rhythm'
  | 'restructure'
  | 'suggest_rhymes'
  | 'improve_lyrics';

export interface QuickAction {
  id: QuickActionType;
  label: string;
  description: string;
  icon?: string;
}

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'full_review',
    label: 'Full Review',
    description: 'Get comprehensive feedback on your song',
  },
  {
    id: 'check_cliches',
    label: 'Check Cliches',
    description: 'Find overused phrases and cliches',
  },
  {
    id: 'analyze_rhythm',
    label: 'Analyze Rhythm',
    description: 'Check syllable counts and flow',
  },
  {
    id: 'restructure',
    label: 'Restructure',
    description: 'Suggest structural improvements',
  },
  {
    id: 'suggest_rhymes',
    label: 'Find Rhymes',
    description: 'Get rhyme suggestions',
  },
  {
    id: 'improve_lyrics',
    label: 'Improve Lyrics',
    description: 'Get lyric enhancement ideas',
  },
];
