'use client';

import { QuickActionType, QUICK_ACTIONS } from '@/types/chat';

interface QuickActionsBarProps {
  onAction: (action: QuickActionType) => void;
  disabled?: boolean;
}

export function QuickActionsBar({ onAction, disabled = false }: QuickActionsBarProps) {
  return (
    <div className="flex gap-2 p-3 overflow-x-auto border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
      {QUICK_ACTIONS.map((action) => (
        <button
          key={action.id}
          onClick={() => onAction(action.id)}
          disabled={disabled}
          className="
            flex-shrink-0
            px-3 py-1.5
            text-xs font-medium
            bg-white dark:bg-gray-700
            text-gray-700 dark:text-gray-200
            border border-gray-200 dark:border-gray-600
            rounded-full
            hover:bg-indigo-50 dark:hover:bg-indigo-900/30
            hover:border-indigo-300 dark:hover:border-indigo-600
            hover:text-indigo-700 dark:hover:text-indigo-300
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors
          "
          title={action.description}
        >
          {action.label}
        </button>
      ))}
    </div>
  );
}
