'use client';

import { useEffect, useRef, useMemo, useCallback } from 'react';
import { Song, SectionType } from '@/types';
import { useChatSession } from '@/hooks/useChatSession';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import type { ChatMessage as ChatMessageType } from '@/types/chat';

interface AIChatPanelProps {
  song: Song;
  onSongUpdated?: () => void; // Callback to refresh song data
}

/**
 * Check if the song is in early exploration phase (no sections or content yet).
 * Used to customize the UI placeholder text.
 */
function isExplorationPhase(song: Song): boolean {
  if (!song.sections || song.sections.length === 0) {
    return true;
  }
  // If all sections are BRAIN_DUMP or empty, we're still exploring
  const hasRealContent = song.sections.some(section => {
    if (section.type === SectionType.BRAIN_DUMP) return false;
    return section.lines && section.lines.some(line => line.text.trim());
  });
  return !hasRealContent;
}

export function AIChatPanel({ song, onSongUpdated }: AIChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Handle song updates from the orchestrator
  const handleSongUpdated = useCallback(() => {
    onSongUpdated?.();
  }, [onSongUpdated]);

  const {
    messages,
    isProcessing,
    progress,
    currentAssistantMessageId,
    sendMessage,
  } = useChatSession({
    songId: song.id,
    onSongUpdated: handleSongUpdated,
  });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, progress.streamedText]);

  // Build display messages with streaming content (memoized to prevent unnecessary re-renders)
  const displayMessages = useMemo<ChatMessageType[]>(() => {
    return messages.map((msg) => {
      if (msg.id === currentAssistantMessageId && progress.streamedText) {
        return {
          ...msg,
          content: progress.streamedText,
          isStreaming: progress.status === 'running',
          metadata: progress.status === 'completed' && progress.result
            ? {
                duration_ms: progress.result.duration_ms,
                tokens: {
                  input: progress.result.input_tokens,
                  output: progress.result.output_tokens,
                },
                cost: progress.result.total_cost_usd,
              }
            : undefined,
        };
      }
      return msg;
    });
  }, [messages, currentAssistantMessageId, progress.streamedText, progress.status, progress.result]);

  // Check if we're in exploration phase for UI customization
  const isExploring = isExplorationPhase(song);

  // Unified header
  const headerTitle = 'Songwriting Collaborator';
  const headerIcon = (
    <svg className="w-5 h-5 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
    </svg>
  );

  // Contextual empty state
  const emptyStateContent = isExploring ? (
    <>
      <svg className="w-12 h-12 mb-3 opacity-50 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
      <p className="text-sm font-medium mb-1">Let's write a song together</p>
      <p className="text-xs max-w-[220px]">
        Tell me about your idea, theme, or paste some lyrics. I can help explore, write, or refine.
      </p>
    </>
  ) : (
    <>
      <svg className="w-12 h-12 mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
      <p className="text-sm font-medium mb-1">Songwriting Collaborator</p>
      <p className="text-xs max-w-[200px]">
        Ask me anything - I can write lyrics, give feedback, restructure, or brainstorm
      </p>
    </>
  );

  const inputPlaceholder = isProcessing
    ? 'AI is thinking...'
    : isExploring
      ? 'What do you want this song to be about?'
      : 'Ask me anything about your song...';

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center gap-2">
          {headerIcon}
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">{headerTitle}</h2>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {displayMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-gray-500 dark:text-gray-400">
            {emptyStateContent}
          </div>
        ) : (
          <>
            {displayMessages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        disabled={isProcessing}
        placeholder={inputPlaceholder}
      />
    </div>
  );
}
