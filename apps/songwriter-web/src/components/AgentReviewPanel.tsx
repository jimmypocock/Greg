'use client';

import { useState } from 'react';
import { useAgentTask } from '@/lib/agentHooks';
import { AgentProgress } from './AgentProgress';

interface AgentReviewPanelProps {
  songId: string;
  hasSections: boolean;
}

export function AgentReviewPanel({ songId, hasSections }: AgentReviewPanelProps) {
  const [currentTaskType, setCurrentTaskType] = useState<string | null>(null);
  const {
    taskResponse,
    progress,
    finalResult,
    error,
    isStarting,
    isRunning,
    isComplete,
    isFailed,
    runTask,
    reset,
  } = useAgentTask(songId);

  const isLoading = isStarting || isRunning;

  const handleReview = async (action: 'full' | 'cliches' | 'rhythm') => {
    const taskTypeMap = {
      full: 'full_review',
      cliches: 'check_cliches',
      rhythm: 'analyze_rhythm',
    };
    setCurrentTaskType(taskTypeMap[action]);
    runTask(action);
  };

  if (!hasSections) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-700">AI Review</h3>
        <p className="mt-1 text-sm text-gray-500">
          Add some sections to your song to enable AI review.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-medium text-gray-900 mb-3">AI Critic</h3>

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => handleReview('full')}
          disabled={isLoading}
          className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading && currentTaskType === 'full_review' ? 'Reviewing...' : 'Full Review'}
        </button>
        <button
          onClick={() => handleReview('cliches')}
          disabled={isLoading}
          className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading && currentTaskType === 'check_cliches' ? 'Checking...' : 'Check Cliches'}
        </button>
        <button
          onClick={() => handleReview('rhythm')}
          disabled={isLoading}
          className="px-3 py-1.5 text-sm bg-teal-600 text-white rounded-md hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading && currentTaskType === 'analyze_rhythm' ? 'Analyzing...' : 'Analyze Rhythm'}
        </button>
      </div>

      {/* Progress indicator during task execution */}
      {(isStarting || isRunning) && (
        <div className="mt-4">
          <AgentProgress progress={progress} taskType={currentTaskType || undefined} />
        </div>
      )}

      {/* Error display */}
      {(error || isFailed) && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-700">{error || progress.error || 'Task failed'}</p>
          <button
            onClick={reset}
            className="mt-2 text-xs text-red-600 hover:text-red-800 underline"
          >
            Try again
          </button>
        </div>
      )}

      {/* Result display */}
      {isComplete && finalResult && (
        <div className="mt-4 p-4 bg-gray-50 rounded-md">
          <div className="flex items-start justify-between mb-2">
            <span className="text-xs font-medium text-gray-500 uppercase">
              {currentTaskType?.replace(/_/g, ' ') || 'Review'}
            </span>
            <span className="text-xs text-gray-400">
              {finalResult.duration_ms}ms
              {finalResult.total_cost_usd && finalResult.total_cost_usd !== '0' && (
                <> | ${parseFloat(finalResult.total_cost_usd).toFixed(6)}</>
              )}
            </span>
          </div>
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">
              {finalResult.result}
            </pre>
          </div>
          {(finalResult.input_tokens > 0 || finalResult.output_tokens > 0) && (
            <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between text-xs text-gray-400">
              <span>
                Tokens: {finalResult.input_tokens} in / {finalResult.output_tokens} out
              </span>
            </div>
          )}
          <button
            onClick={reset}
            className="mt-3 text-xs text-gray-500 hover:text-gray-700 underline"
          >
            Clear result
          </button>
        </div>
      )}

      {/* WebSocket-delivered result from progress (backup) */}
      {isComplete && progress.result && !finalResult && (
        <div className="mt-4 p-4 bg-gray-50 rounded-md">
          <div className="flex items-start justify-between mb-2">
            <span className="text-xs font-medium text-gray-500 uppercase">
              {currentTaskType?.replace(/_/g, ' ') || 'Review'}
            </span>
          </div>
          <div className="prose prose-sm max-w-none">
            <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">
              {progress.result.result}
            </pre>
          </div>
          <button
            onClick={reset}
            className="mt-3 text-xs text-gray-500 hover:text-gray-700 underline"
          >
            Clear result
          </button>
        </div>
      )}
    </div>
  );
}
