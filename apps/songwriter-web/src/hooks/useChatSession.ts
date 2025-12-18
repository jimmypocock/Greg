'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { ChatMessage, QuickActionType } from '@/types/chat';

// Generate unique message IDs using crypto.randomUUID()
// This is safe for SSR and avoids module-level state
function generateId(): string {
  return `msg-${crypto.randomUUID()}`;
}
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket';
import {
  reviewSong,
  checkCliches,
  analyzeRhythm,
  chatWithSong,
} from '@/lib/agents';

interface UseChatSessionOptions {
  songId: string;
}

export function useChatSession({ songId }: UseChatSessionOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentAssistantMessageId, setCurrentAssistantMessageId] = useState<string | null>(null);

  // Track the previous status to detect transitions
  const prevStatusRef = useRef<string>('idle');

  // Handle agent error
  const handleError = useCallback((error: string) => {
    setIsProcessing(false);
    setMessages((prev) => {
      const msgId = currentAssistantMessageId;
      if (msgId) {
        return prev.map((msg) =>
          msg.id === msgId
            ? { ...msg, content: `Error: ${error}`, isStreaming: false }
            : msg
        );
      }
      return prev;
    });
    setCurrentAssistantMessageId(null);
  }, [currentAssistantMessageId]);

  const websocket = useAgentWebSocket({
    onError: handleError,
  });

  const { progress } = websocket;

  // Effect to persist streamed text when task completes
  useEffect(() => {
    const prevStatus = prevStatusRef.current;
    const currentStatus = progress.status;

    // Detect transition to completed or failed
    if (prevStatus === 'running' && (currentStatus === 'completed' || currentStatus === 'failed')) {
      if (currentAssistantMessageId && progress.streamedText) {
        // Persist the streamed text to the message
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === currentAssistantMessageId
              ? {
                  ...msg,
                  content: progress.streamedText,
                  isStreaming: false,
                  metadata: progress.result
                    ? {
                        duration_ms: progress.result.duration_ms,
                        tokens: {
                          input: progress.result.input_tokens,
                          output: progress.result.output_tokens,
                        },
                        cost: progress.result.total_cost_usd,
                      }
                    : undefined,
                }
              : msg
          )
        );
      }
      setIsProcessing(false);
      setCurrentAssistantMessageId(null);
    }

    prevStatusRef.current = currentStatus;
  }, [progress.status, progress.streamedText, progress.result, currentAssistantMessageId]);

  const addUserMessage = useCallback((content: string): ChatMessage => {
    const message: ChatMessage = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, message]);
    return message;
  }, []);

  const addAssistantMessage = useCallback((content: string = '', isStreaming: boolean = false): ChatMessage => {
    const message: ChatMessage = {
      id: generateId(),
      role: 'assistant',
      content,
      timestamp: new Date(),
      isStreaming,
    };
    setMessages((prev) => [...prev, message]);
    setCurrentAssistantMessageId(message.id);
    return message;
  }, []);

  const updateAssistantMessage = useCallback((messageId: string, updates: Partial<ChatMessage>) => {
    setMessages((prev) =>
      prev.map((msg) =>
        msg.id === messageId ? { ...msg, ...updates } : msg
      )
    );
  }, []);

  const runQuickAction = useCallback(async (action: QuickActionType) => {
    if (isProcessing) return;

    setIsProcessing(true);

    // User-facing labels for display
    const actionLabels: Record<QuickActionType, string> = {
      full_review: 'Give me a full review of my song',
      check_cliches: 'Check my song for cliches',
      analyze_rhythm: 'Analyze the rhythm and syllable counts',
      restructure: 'Suggest how to restructure my song',
      suggest_rhymes: 'Help me find better rhymes',
      improve_lyrics: 'Suggest specific lyric improvements',
    };

    // More detailed prompts for chat-based actions
    const chatPrompts: Record<string, string> = {
      restructure: `Look at my song's current structure and suggest how I could restructure it. Consider:
- Whether sections are in the best order
- If any sections should be added, removed, or combined
- How the emotional arc could be improved through structure changes
Give me specific, actionable suggestions.`,
      suggest_rhymes: `Review my lyrics and identify lines that could benefit from better rhymes. For each opportunity:
- Quote the specific line
- Explain what's currently there
- Suggest 2-3 alternative rhyme options that maintain the meaning
Focus on rhymes that feel natural, not forced.`,
      improve_lyrics: `Review my lyrics line by line and suggest specific improvements. For each suggestion:
- Quote the original line
- Explain what could be better (weak word choice, vague imagery, awkward phrasing, etc.)
- Provide 1-2 rewritten alternatives
Focus on making the lyrics more vivid, emotional, and impactful without changing the core meaning.`,
    };

    addUserMessage(actionLabels[action]);

    // Add placeholder assistant message
    const assistantMsg = addAssistantMessage('', true);

    try {
      let response;

      switch (action) {
        case 'full_review':
          response = await reviewSong(songId);
          break;
        case 'check_cliches':
          response = await checkCliches(songId);
          break;
        case 'analyze_rhythm':
          response = await analyzeRhythm(songId);
          break;
        case 'restructure':
        case 'suggest_rhymes':
        case 'improve_lyrics':
          // Use chat endpoint with specific prompts
          response = await chatWithSong(songId, chatPrompts[action], []);
          break;
        default:
          throw new Error(`Unknown action: ${action}`);
      }

      // Connect to WebSocket for streaming
      websocket.connect(response.task_id);

      // Update message with task ID
      updateAssistantMessage(assistantMsg.id, { taskId: response.task_id });
    } catch (error) {
      setIsProcessing(false);
      updateAssistantMessage(assistantMsg.id, {
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        isStreaming: false,
      });
    }
  }, [songId, isProcessing, addUserMessage, addAssistantMessage, updateAssistantMessage, websocket]);

  const sendMessage = useCallback(async (content: string) => {
    if (isProcessing || !content.trim()) return;

    setIsProcessing(true);

    // Add user message
    addUserMessage(content);

    // Add placeholder assistant message
    const assistantMsg = addAssistantMessage('', true);

    try {
      // Build conversation history from previous messages (excluding the just-added user message)
      // Limit to last 20 messages for context window management
      const conversationHistory = messages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .slice(-20)
        .map(msg => ({
          role: msg.role as 'user' | 'assistant',
          content: msg.content,
        }));

      // Call the chat endpoint with the new message and history
      const response = await chatWithSong(songId, content, conversationHistory);

      // Connect to WebSocket for streaming
      websocket.connect(response.task_id);

      // Update message with task ID
      updateAssistantMessage(assistantMsg.id, { taskId: response.task_id, content: '' });
    } catch (error) {
      setIsProcessing(false);
      updateAssistantMessage(assistantMsg.id, {
        content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        isStreaming: false,
      });
    }
  }, [songId, isProcessing, messages, addUserMessage, addAssistantMessage, updateAssistantMessage, websocket]);

  const clearHistory = useCallback(() => {
    setMessages([]);
    websocket.reset();
  }, [websocket]);

  return {
    messages,
    isProcessing,
    progress: websocket.progress,
    currentAssistantMessageId,
    sendMessage,
    runQuickAction,
    clearHistory,
  };
}
