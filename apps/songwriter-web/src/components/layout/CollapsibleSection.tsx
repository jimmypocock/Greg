'use client';

import { useState, useEffect, ReactNode } from 'react';

interface CollapsibleSectionProps {
  title: string;
  icon?: ReactNode;
  defaultExpanded?: boolean;
  storageKey?: string;
  children: ReactNode;
  badge?: ReactNode;
}

export function CollapsibleSection({
  title,
  icon,
  defaultExpanded = true,
  storageKey,
  children,
  badge,
}: CollapsibleSectionProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [isInitialized, setIsInitialized] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    if (storageKey) {
      const stored = localStorage.getItem(`collapsible-${storageKey}`);
      if (stored !== null) {
        setIsExpanded(stored === 'true');
      }
    }
    setIsInitialized(true);
  }, [storageKey]);

  // Save to localStorage on change
  useEffect(() => {
    if (storageKey && isInitialized) {
      localStorage.setItem(`collapsible-${storageKey}`, String(isExpanded));
    }
  }, [storageKey, isExpanded, isInitialized]);

  return (
    <div className="border-b border-gray-200 dark:border-gray-700 last:border-b-0">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="
          w-full px-4 py-3
          flex items-center justify-between
          bg-gray-50 dark:bg-gray-800
          hover:bg-gray-100 dark:hover:bg-gray-750
          transition-colors duration-150
          text-left
        "
      >
        <div className="flex items-center gap-2">
          {icon && (
            <span className="text-gray-500 dark:text-gray-400">
              {icon}
            </span>
          )}
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-200 uppercase tracking-wide">
            {title}
          </span>
          {badge}
        </div>
        <svg
          className={`
            w-4 h-4 text-gray-500 dark:text-gray-400
            transition-transform duration-200
            ${isExpanded ? 'rotate-180' : ''}
          `}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <div
        className={`
          overflow-hidden transition-all duration-200 ease-in-out
          ${isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}
        `}
      >
        <div className="p-4 bg-white dark:bg-gray-900">
          {children}
        </div>
      </div>
    </div>
  );
}
