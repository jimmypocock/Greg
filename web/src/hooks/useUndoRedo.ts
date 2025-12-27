'use client';

import { useState, useCallback, useEffect, useRef } from 'react';

interface UndoRedoAction {
  undo: () => Promise<void>;
  redo: () => Promise<void>;
  description: string;
}

interface UseUndoRedoOptions {
  maxHistory?: number;
}

export function useUndoRedo(options: UseUndoRedoOptions = {}) {
  const { maxHistory = 50 } = options;

  const [undoStack, setUndoStack] = useState<UndoRedoAction[]>([]);
  const [redoStack, setRedoStack] = useState<UndoRedoAction[]>([]);
  const [isPerformingAction, setIsPerformingAction] = useState(false);

  // Use ref to track if we're in an undo/redo operation
  const isUndoRedoRef = useRef(false);

  // Refs for callbacks to avoid re-registering event listener
  const undoRef = useRef<() => Promise<void>>(() => Promise.resolve());
  const redoRef = useRef<() => Promise<void>>(() => Promise.resolve());

  const pushAction = useCallback((action: UndoRedoAction) => {
    // Don't push to history if we're currently undoing/redoing
    if (isUndoRedoRef.current) return;

    setUndoStack((prev) => {
      const newStack = [...prev, action];
      // Limit history size
      if (newStack.length > maxHistory) {
        return newStack.slice(-maxHistory);
      }
      return newStack;
    });
    // Clear redo stack when a new action is performed
    setRedoStack([]);
  }, [maxHistory]);

  const undo = useCallback(async () => {
    if (undoStack.length === 0 || isPerformingAction) return;

    const action = undoStack[undoStack.length - 1];
    setIsPerformingAction(true);
    isUndoRedoRef.current = true;

    try {
      await action.undo();
      setUndoStack((prev) => prev.slice(0, -1));
      setRedoStack((prev) => [...prev, action]);
    } catch (error) {
      console.error('Undo failed:', error);
    } finally {
      setIsPerformingAction(false);
      isUndoRedoRef.current = false;
    }
  }, [undoStack, isPerformingAction]);

  const redo = useCallback(async () => {
    if (redoStack.length === 0 || isPerformingAction) return;

    const action = redoStack[redoStack.length - 1];
    setIsPerformingAction(true);
    isUndoRedoRef.current = true;

    try {
      await action.redo();
      setRedoStack((prev) => prev.slice(0, -1));
      setUndoStack((prev) => [...prev, action]);
    } catch (error) {
      console.error('Redo failed:', error);
    } finally {
      setIsPerformingAction(false);
      isUndoRedoRef.current = false;
    }
  }, [redoStack, isPerformingAction]);

  const clearHistory = useCallback(() => {
    setUndoStack([]);
    setRedoStack([]);
  }, []);

  // Keep refs updated with latest callbacks (avoids re-registering event listener)
  useEffect(() => {
    undoRef.current = undo;
    redoRef.current = redo;
  }, [undo, redo]);

  // Keyboard shortcuts - registered once, uses refs for latest callbacks
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
      const modKey = isMac ? e.metaKey : e.ctrlKey;

      if (modKey && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undoRef.current();
      } else if (modKey && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        redoRef.current();
      } else if (modKey && e.key === 'y' && !isMac) {
        // Ctrl+Y for redo on Windows/Linux
        e.preventDefault();
        redoRef.current();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []); // Empty deps - only register once

  return {
    pushAction,
    undo,
    redo,
    clearHistory,
    canUndo: undoStack.length > 0 && !isPerformingAction,
    canRedo: redoStack.length > 0 && !isPerformingAction,
    isPerformingAction,
    undoDescription: undoStack[undoStack.length - 1]?.description,
    redoDescription: redoStack[redoStack.length - 1]?.description,
  };
}
