'use client';

import { useState } from 'react';
import { useReviewHistory } from '@/lib/agentHooks';
import { AgentTaskType } from '@/types/agent';

interface ReviewHistoryProps {
  songId: string;
}

const taskTypeLabels: Record<AgentTaskType, string> = {
  [AgentTaskType.FULL_REVIEW]: 'Full Review',
  [AgentTaskType.SECTION_REVIEW]: 'Section Review',
  [AgentTaskType.CHECK_CLICHES]: 'Cliche Check',
  [AgentTaskType.ANALYZE_RHYTHM]: 'Rhythm Analysis',
};

const taskTypeColors: Record<AgentTaskType, string> = {
  [AgentTaskType.FULL_REVIEW]: 'bg-indigo-100 text-indigo-800',
  [AgentTaskType.SECTION_REVIEW]: 'bg-blue-100 text-blue-800',
  [AgentTaskType.CHECK_CLICHES]: 'bg-purple-100 text-purple-800',
  [AgentTaskType.ANALYZE_RHYTHM]: 'bg-teal-100 text-teal-800',
};

export function ReviewHistory({ songId }: ReviewHistoryProps) {
  const { data, isLoading, error } = useReviewHistory(songId);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-900 mb-3">Review History</h3>
        <div className="animate-pulse space-y-2">
          <div className="h-10 bg-gray-100 rounded"></div>
          <div className="h-10 bg-gray-100 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-900 mb-3">Review History</h3>
        <p className="text-sm text-red-600">Failed to load history</p>
      </div>
    );
  }

  if (!data || data.reviews.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-900 mb-3">Review History</h3>
        <p className="text-sm text-gray-500">No reviews yet. Run an AI review above.</p>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-900">Review History</h3>
        <span className="text-xs text-gray-500">
          Total cost: ${parseFloat(data.total_cost_usd).toFixed(4)}
        </span>
      </div>

      <div className="space-y-2">
        {data.reviews.map((review) => {
          const isExpanded = expandedId === review.id;
          const date = new Date(review.created_at);
          const formattedDate = date.toLocaleDateString();
          const formattedTime = date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          });

          return (
            <div
              key={review.id}
              className="border border-gray-100 rounded-md overflow-hidden"
            >
              <button
                onClick={() => setExpandedId(isExpanded ? null : review.id)}
                className="w-full flex items-center justify-between p-3 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-medium ${
                      taskTypeColors[review.task_type] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {taskTypeLabels[review.task_type] || review.task_type}
                  </span>
                  <span className="text-xs text-gray-400">
                    {formattedDate} {formattedTime}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">
                    ${parseFloat(review.total_cost_usd).toFixed(6)}
                  </span>
                  <svg
                    className={`w-4 h-4 text-gray-400 transition-transform ${
                      isExpanded ? 'rotate-180' : ''
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </div>
              </button>

              {isExpanded && (
                <div className="p-3 bg-gray-50 border-t border-gray-100">
                  <pre className="whitespace-pre-wrap font-sans text-sm text-gray-700">
                    {review.result}
                  </pre>
                  <div className="mt-3 pt-3 border-t border-gray-200 flex items-center justify-between text-xs text-gray-400">
                    <span>
                      Tokens: {review.input_tokens} in / {review.output_tokens} out
                      {review.duration_ms && ` | ${review.duration_ms}ms`}
                    </span>
                    {review.model && <span>Model: {review.model}</span>}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
