'use client';

import type { AgentProgress as AgentProgressType } from '@/hooks/useAgentWebSocket';

interface AgentProgressProps {
  progress: AgentProgressType;
  taskType?: string;
}

export function AgentProgress({ progress, taskType }: AgentProgressProps) {
  const { status, agentName, currentActivity, thoughts, toolsUsed, streamedText } = progress;

  if (status === 'idle') {
    return null;
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 animate-in fade-in duration-300">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusIndicator status={status} />
          <span className="text-sm font-medium text-gray-700">
            {agentName || 'AI Critic'}
          </span>
        </div>
        {taskType && (
          <span className="text-xs text-gray-500 uppercase">
            {taskType.replace(/_/g, ' ')}
          </span>
        )}
      </div>

      {/* Current Activity */}
      {currentActivity && (
        <div className="mb-3">
          <div className="flex items-center gap-2">
            {status === 'running' && (
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            )}
            <span className="text-sm text-gray-600">{currentActivity}</span>
          </div>
        </div>
      )}

      {/* Tools Used */}
      {toolsUsed.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-1">Tools Used</div>
          <div className="flex flex-wrap gap-1">
            {toolsUsed.map((tool, index) => (
              <span
                key={`${tool.name}-${index}`}
                className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-gray-200 text-gray-700"
              >
                {formatToolName(tool.name)}
                {tool.output && (
                  <span className="ml-1 text-green-600" title={tool.output}>
                    ✓
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Streamed Response */}
      {streamedText && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-2">Response</div>
          <div className="bg-white border border-gray-200 rounded p-3 max-h-64 overflow-y-auto">
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
              {streamedText}
              {status === 'running' && (
                <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-0.5" />
              )}
            </pre>
          </div>
        </div>
      )}

      {/* Recent Activity - shown expanded */}
      {thoughts.length > 0 && (
        <div className="mb-3">
          <div className="text-xs text-gray-500 mb-2">Recent Activity</div>
          <div className="space-y-1.5 pl-2 border-l-2 border-blue-200 max-h-48 overflow-y-auto">
            {thoughts.slice(-8).map((thought, index) => (
              <p
                key={index}
                className="text-sm text-gray-700 leading-relaxed"
              >
                {thought}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Loading animation for connecting/running states */}
      {(status === 'connecting' || status === 'running') && (
        <div className="mt-3 h-1 bg-gray-200 rounded-full overflow-hidden">
          <div className="h-full bg-blue-500 rounded-full animate-progress" />
        </div>
      )}
    </div>
  );
}

function StatusIndicator({ status }: { status: AgentProgressType['status'] }) {
  switch (status) {
    case 'connecting':
      return (
        <div className="w-3 h-3 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
      );
    case 'running':
      return (
        <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
      );
    case 'completed':
      return (
        <div className="w-3 h-3 bg-green-500 rounded-full" />
      );
    case 'failed':
      return (
        <div className="w-3 h-3 bg-red-500 rounded-full" />
      );
    default:
      return null;
  }
}

function formatToolName(name: string): string {
  return name
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (str) => str.toUpperCase())
    .trim();
}
