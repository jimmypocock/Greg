'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { ChatMessage, QuickActionType } from '@/types/chat';

// Generate unique message IDs using crypto.randomUUID()
function generateId(): string {
  return `msg-${crypto.randomUUID()}`;
}
import { useAgentWebSocket } from '@/hooks/useAgentWebSocket';
import {
  reviewSong,
  checkCliches,
  analyzeRhythm,
  chatWithSong,
  getChatHistory,
  clearChatHistory,
} from '@/lib/agents';

interface UseChatSessionOptions {
  songId: string;
  onSongUpdated?: () => void; // Callback when song data changes
}

export function useChatSession({ songId, onSongUpdated }: UseChatSessionOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentAssistantMessageId, setCurrentAssistantMessageId] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  // Track the previous status to detect transitions
  const prevStatusRef = useRef<string>('idle');

  // Track callback ref for onSongUpdated
  const onSongUpdatedRef = useRef(onSongUpdated);
  onSongUpdatedRef.current = onSongUpdated;

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

  // Handle custom events like song.updated
  const handleCustomEvent = useCallback((eventType: string, _data: unknown) => {
    if (eventType === 'song.updated' && onSongUpdatedRef.current) {
      onSongUpdatedRef.current();
    }
  }, []);

  const websocket = useAgentWebSocket({
    onError: handleError,
    onCustomEvent: handleCustomEvent,
  });

  const { progress } = websocket;

  // Load chat history from API on mount
  useEffect(() => {
    let mounted = true;

    async function loadHistory() {
      try {
        const response = await getChatHistory(songId);
        if (mounted) {
          // Convert API messages to ChatMessage format
          const loadedMessages: ChatMessage[] = response.messages.map((msg) => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            timestamp: new Date(msg.created_at),
            metadata: msg.role === 'assistant' && (msg.input_tokens || msg.output_tokens || msg.total_cost_usd)
              ? {
                  duration_ms: msg.duration_ms,
                  tokens: {
                    input: msg.input_tokens || 0,
                    output: msg.output_tokens || 0,
                  },
                  cost: msg.total_cost_usd,
                }
              : undefined,
          }));
          setMessages(loadedMessages);
          setIsLoadingHistory(false);
        }
      } catch (error) {
        console.error('Failed to load chat history:', error);
        if (mounted) {
          setIsLoadingHistory(false);
        }
      }
    }

    loadHistory();

    return () => {
      mounted = false;
    };
  }, [songId]);

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

    // Add user message to local state for immediate display
    addUserMessage(content);

    // Add placeholder assistant message
    const assistantMsg = addAssistantMessage('', true);

    try {
      // Call the unified chat endpoint
      // Note: Backend loads conversation history from database, no need to send it
      const response = await chatWithSong(songId, content, []);

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
  }, [songId, isProcessing, addUserMessage, addAssistantMessage, updateAssistantMessage, websocket]);

  const clearHistory = useCallback(async () => {
    try {
      // Clear history from server
      await clearChatHistory(songId);
      // Clear local state
      setMessages([]);
      websocket.reset();
    } catch (error) {
      console.error('Failed to clear chat history:', error);
    }
  }, [songId, websocket]);

  return {
    messages,
    isProcessing,
    isLoadingHistory,
    progress: websocket.progress,
    currentAssistantMessageId,
    sendMessage,
    runQuickAction,
    clearHistory,
  };
}
