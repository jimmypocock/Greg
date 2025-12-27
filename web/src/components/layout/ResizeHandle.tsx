'use client';

import { useCallback, useEffect, useState } from 'react';

interface ResizeHandleProps {
  onResize: (delta: number) => void;
  onResizeEnd?: () => void;
}

export function ResizeHandle({ onResize, onResizeEnd }: ResizeHandleProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    setIsDragging(true);
    setStartX(e.clientX);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, []);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    const delta = e.clientX - startX;
    setStartX(e.clientX);
    onResize(delta);
  }, [isDragging, startX, onResize]);

  const handlePointerUp = useCallback((e: React.PointerEvent) => {
    if (!isDragging) return;
    setIsDragging(false);
    (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    onResizeEnd?.();
  }, [isDragging, onResizeEnd]);

  // Prevent text selection while dragging
  useEffect(() => {
    if (isDragging) {
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
    } else {
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    }
    return () => {
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDragging]);

  return (
    <div
      className={`
        w-2 cursor-col-resize flex-shrink-0
        bg-gradient-to-r from-transparent via-gray-200 to-transparent
        hover:via-indigo-300
        transition-colors duration-150
        ${isDragging ? 'via-indigo-400' : ''}
      `}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      <div className="h-full w-full flex items-center justify-center">
        <div className={`
          w-1 h-8 rounded-full
          bg-gray-300 hover:bg-indigo-400
          transition-colors duration-150
          ${isDragging ? 'bg-indigo-500' : ''}
        `} />
      </div>
    </div>
  );
}
