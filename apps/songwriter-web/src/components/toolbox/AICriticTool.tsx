'use client';

import { AgentReviewPanel } from '@/components/AgentReviewPanel';
import { ReviewHistory } from '@/components/ReviewHistory';

interface AICriticToolProps {
  songId: string;
  hasSections: boolean;
}

export function AICriticTool({ songId, hasSections }: AICriticToolProps) {
  return (
    <div className="space-y-4">
      <AgentReviewPanel songId={songId} hasSections={hasSections} />
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <ReviewHistory songId={songId} />
      </div>
    </div>
  );
}
