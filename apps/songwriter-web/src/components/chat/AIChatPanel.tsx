'use client';

import { useEffect, useRef } from 'react';
import { Song } from '@/types';
import { useChatSession } from '@/hooks/useChatSession';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { QuickActionsBar } from './QuickActionsBar';
import type { ChatMessage as ChatMessageType } from '@/types/chat';

interface AIChatPanelProps {
  song: Song;
  onClose?: () => void;
}

export function AIChatPanel({ song, onClose }: AIChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    messages,
    isProcessing,
    progress,
    currentAssistantMessageId,
    sendMessage,
    runQuickAction,
    clearHistory,
  } = useChatSession({ songId: song.id });

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, progress.streamedText]);

  // Build display messages with streaming content
  const displayMessages: ChatMessageType[] = messages.map((msg) => {
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

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-600 dark:text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">AI Assistant</h2>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              onClick={clearHistory}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              title="Clear chat history"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              title="Close AI Assistant"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <QuickActionsBar onAction={runQuickAction} disabled={isProcessing} />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1">
        {displayMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-gray-500 dark:text-gray-400">
            <svg className="w-12 h-12 mb-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-sm font-medium mb-1">AI Songwriting Assistant</p>
            <p className="text-xs max-w-[200px]">
              Use the quick actions above or ask me anything about your song
            </p>
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
        placeholder={isProcessing ? 'AI is thinking...' : 'Ask about your song...'}
      />
    </div>
  );
}
