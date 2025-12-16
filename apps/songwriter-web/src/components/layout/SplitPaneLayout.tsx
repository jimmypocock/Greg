'use client';

import { ReactNode, useState, useEffect, useCallback } from 'react';
import { ResizeHandle } from './ResizeHandle';

interface SplitPaneLayoutProps {
  leftPanel: ReactNode;
  rightPanel: ReactNode;
  defaultLeftWidth?: number;
  minLeftWidth?: number;
  maxLeftWidth?: number;
  minRightWidth?: number;
  storageKey?: string;
}

export function SplitPaneLayout({
  leftPanel,
  rightPanel,
  defaultLeftWidth = 420,
  minLeftWidth = 320,
  maxLeftWidth = 600,
  minRightWidth = 400,
  storageKey = 'split-pane-width',
}: SplitPaneLayoutProps) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [isInitialized, setIsInitialized] = useState(false);

  // Load from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      const width = parseInt(stored, 10);
      if (!isNaN(width)) {
        setLeftWidth(Math.max(minLeftWidth, Math.min(maxLeftWidth, width)));
      }
    }
    setIsInitialized(true);
  }, [storageKey, minLeftWidth, maxLeftWidth]);

  // Handle resize
  const handleResize = useCallback((delta: number) => {
    setLeftWidth((prev) => {
      const newWidth = prev + delta;
      // Check if we have enough space on the right
      const availableWidth = window.innerWidth;
      const maxAllowed = Math.min(maxLeftWidth, availableWidth - minRightWidth - 8); // 8px for handle
      return Math.max(minLeftWidth, Math.min(maxAllowed, newWidth));
    });
  }, [minLeftWidth, maxLeftWidth, minRightWidth]);

  // Save to localStorage when resize ends
  const handleResizeEnd = useCallback(() => {
    localStorage.setItem(storageKey, String(leftWidth));
  }, [storageKey, leftWidth]);

  // Don't render until initialized to prevent flash
  if (!isInitialized) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden bg-gray-100 dark:bg-gray-900 min-h-0">
      {/* Left Panel - Toolbox */}
      <div
        style={{ width: leftWidth }}
        className="flex-shrink-0 flex flex-col bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-hidden min-h-0"
      >
        <div className="flex-1 overflow-y-auto overflow-x-hidden min-h-0">
          {leftPanel}
        </div>
      </div>

      {/* Resize Handle */}
      <ResizeHandle onResize={handleResize} onResizeEnd={handleResizeEnd} />

      {/* Right Panel - Live Preview */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden min-h-0">
        {rightPanel}
      </div>
    </div>
  );
}
