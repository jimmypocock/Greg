'use client';

import { ReactNode, useState, useEffect, useCallback } from 'react';
import { ResizeHandle } from './ResizeHandle';

interface ThreePaneLayoutProps {
  leftPanel: ReactNode;
  centerPanel: ReactNode;
  rightPanel: ReactNode;
  defaultLeftWidth?: number;
  minLeftWidth?: number;
  maxLeftWidth?: number;
  defaultRightWidth?: number;
  minRightWidth?: number;
  maxRightWidth?: number;
  minCenterWidth?: number;
  rightPanelOpen?: boolean;
  onRightPanelToggle?: (open: boolean) => void;
  storageKeyLeft?: string;
  storageKeyRight?: string;
  storageKeyRightOpen?: string;
}

export function ThreePaneLayout({
  leftPanel,
  centerPanel,
  rightPanel,
  defaultLeftWidth = 420,
  minLeftWidth = 320,
  maxLeftWidth = 600,
  defaultRightWidth = 380,
  minRightWidth = 300,
  maxRightWidth = 500,
  minCenterWidth = 300,
  rightPanelOpen: controlledRightPanelOpen,
  onRightPanelToggle,
  storageKeyLeft = 'three-pane-left-width',
  storageKeyRight = 'three-pane-right-width',
  storageKeyRightOpen = 'three-pane-right-open',
}: ThreePaneLayoutProps) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [rightWidth, setRightWidth] = useState(defaultRightWidth);
  const [internalRightOpen, setInternalRightOpen] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false);

  // Use controlled or internal state for right panel
  const rightOpen = controlledRightPanelOpen ?? internalRightOpen;
  const setRightOpen = onRightPanelToggle ?? setInternalRightOpen;

  // Load from localStorage on mount
  useEffect(() => {
    const storedLeft = localStorage.getItem(storageKeyLeft);
    if (storedLeft) {
      const width = parseInt(storedLeft, 10);
      if (!isNaN(width)) {
        setLeftWidth(Math.max(minLeftWidth, Math.min(maxLeftWidth, width)));
      }
    }

    const storedRight = localStorage.getItem(storageKeyRight);
    if (storedRight) {
      const width = parseInt(storedRight, 10);
      if (!isNaN(width)) {
        setRightWidth(Math.max(minRightWidth, Math.min(maxRightWidth, width)));
      }
    }

    const storedRightOpen = localStorage.getItem(storageKeyRightOpen);
    if (storedRightOpen !== null) {
      setInternalRightOpen(storedRightOpen === 'true');
    }

    setIsInitialized(true);
  }, [storageKeyLeft, storageKeyRight, storageKeyRightOpen, minLeftWidth, maxLeftWidth, minRightWidth, maxRightWidth]);

  // Handle left resize
  const handleLeftResize = useCallback((delta: number) => {
    setLeftWidth((prev) => {
      const newWidth = prev + delta;
      const availableWidth = window.innerWidth;
      const rightPanelWidth = rightOpen ? rightWidth + 8 : 0; // 8px for handle
      const maxAllowed = Math.min(maxLeftWidth, availableWidth - minCenterWidth - rightPanelWidth - 8);
      return Math.max(minLeftWidth, Math.min(maxAllowed, newWidth));
    });
  }, [minLeftWidth, maxLeftWidth, minCenterWidth, rightOpen, rightWidth]);

  // Handle right resize
  const handleRightResize = useCallback((delta: number) => {
    setRightWidth((prev) => {
      // Delta is negative when dragging left (making right panel larger)
      const newWidth = prev - delta;
      const availableWidth = window.innerWidth;
      const maxAllowed = Math.min(maxRightWidth, availableWidth - leftWidth - minCenterWidth - 16);
      return Math.max(minRightWidth, Math.min(maxAllowed, newWidth));
    });
  }, [minRightWidth, maxRightWidth, minCenterWidth, leftWidth]);

  // Save to localStorage when resize ends
  const handleLeftResizeEnd = useCallback(() => {
    localStorage.setItem(storageKeyLeft, String(leftWidth));
  }, [storageKeyLeft, leftWidth]);

  const handleRightResizeEnd = useCallback(() => {
    localStorage.setItem(storageKeyRight, String(rightWidth));
  }, [storageKeyRight, rightWidth]);

  // Save right panel open state
  useEffect(() => {
    if (isInitialized) {
      localStorage.setItem(storageKeyRightOpen, String(rightOpen));
    }
  }, [rightOpen, storageKeyRightOpen, isInitialized]);

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

      {/* Left Resize Handle */}
      <ResizeHandle onResize={handleLeftResize} onResizeEnd={handleLeftResizeEnd} />

      {/* Center Panel - Live Preview */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden min-h-0">
        {centerPanel}
      </div>

      {/* Right Panel - AI Chat (when open) */}
      {rightOpen && (
        <>
          {/* Right Resize Handle */}
          <ResizeHandle onResize={handleRightResize} onResizeEnd={handleRightResizeEnd} />

          {/* Right Panel */}
          <div
            style={{ width: rightWidth }}
            className="flex-shrink-0 flex flex-col bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 overflow-hidden min-h-0"
          >
            <div className="flex-1 overflow-hidden min-h-0 flex flex-col">
              {rightPanel}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
