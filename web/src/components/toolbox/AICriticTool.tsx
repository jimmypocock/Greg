'use client';

import { ReviewHistory } from '@/components/ReviewHistory';

interface ConversationHistoryToolProps {
  songId: string;
}

export function ConversationHistoryTool({ songId }: ConversationHistoryToolProps) {
  return (
    <div>
      <ReviewHistory songId={songId} />
    </div>
  );
}
