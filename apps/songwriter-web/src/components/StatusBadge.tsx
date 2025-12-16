'use client';

import { SongStatus } from '@/types';

const statusStyles: Record<SongStatus, { bg: string; text: string }> = {
  [SongStatus.IDEA]: { bg: 'bg-gray-100', text: 'text-gray-700' },
  [SongStatus.DRAFT]: { bg: 'bg-yellow-100', text: 'text-yellow-800' },
  [SongStatus.IN_PROGRESS]: { bg: 'bg-blue-100', text: 'text-blue-800' },
  [SongStatus.REVIEW]: { bg: 'bg-purple-100', text: 'text-purple-800' },
  [SongStatus.FINISHED]: { bg: 'bg-green-100', text: 'text-green-800' },
};

const statusLabels: Record<SongStatus, string> = {
  [SongStatus.IDEA]: 'Idea',
  [SongStatus.DRAFT]: 'Draft',
  [SongStatus.IN_PROGRESS]: 'In Progress',
  [SongStatus.REVIEW]: 'Review',
  [SongStatus.FINISHED]: 'Finished',
};

interface StatusBadgeProps {
  status: SongStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const style = statusStyles[status] || statusStyles[SongStatus.IDEA];
  const label = statusLabels[status] || status;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}
    >
      {label}
    </span>
  );
}
