'use client';

import { ChatMessage as ChatMessageType } from '@/types/chat';

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="px-3 py-1 text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 rounded-full">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
      <div
        className={`
          max-w-[85%] px-3 py-2 rounded-lg
          ${isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-bl-sm'
          }
        `}
      >
        {/* Message content */}
        <div className="text-sm whitespace-pre-wrap break-words">
          {message.content || (message.isStreaming ? (
            <span className="text-gray-400 dark:text-gray-500 italic">Thinking...</span>
          ) : null)}
          {message.isStreaming && message.content && (
            <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
          )}
        </div>

        {/* Metadata (for assistant messages) */}
        {!isUser && message.metadata && !message.isStreaming && (
          <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400">
            {message.metadata.tokens && (
              <span>
                {message.metadata.tokens.input + message.metadata.tokens.output} tokens
              </span>
            )}
            {message.metadata.cost && (
              <span className="ml-2">${message.metadata.cost}</span>
            )}
            {message.metadata.duration_ms && (
              <span className="ml-2">{(message.metadata.duration_ms / 1000).toFixed(1)}s</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
