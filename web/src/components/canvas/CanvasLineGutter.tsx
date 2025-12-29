'use client';

/**
 * Canvas Line Gutter
 *
 * Left-side gutter showing line type icon with dropdown to change type.
 */

import { useState, useRef, useEffect } from 'react';
import { LineType } from '@/types/song';
import { LINE_TYPE_CONFIGS, LineTypeConfig } from './types';

interface CanvasLineGutterProps {
  lineType: LineType;
  onTypeChange: (newType: LineType) => void;
  isDragging?: boolean;
}

export function CanvasLineGutter({
  lineType,
  onTypeChange,
  isDragging,
}: CanvasLineGutterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  const config = LINE_TYPE_CONFIGS[lineType];

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Close on escape
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen]);

  const handleTypeSelect = (type: LineType) => {
    onTypeChange(type);
    setIsOpen(false);
  };

  return (
    <div className="relative flex items-center">
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        className={`
          w-6 h-5 flex items-center justify-center
          text-gray-300 hover:text-gray-500 dark:text-gray-600 dark:hover:text-gray-400
          transition-colors text-xs
          ${isDragging ? 'cursor-grabbing' : 'cursor-pointer'}
        `}
        title={`${config.label} (click to change)`}
        aria-label={`Line type: ${config.label}. Click to change.`}
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <span className="select-none">{config.icon}</span>
      </button>

      {isOpen && (
        <div
          ref={menuRef}
          className="
            absolute left-0 top-full mt-1 z-50
            bg-white dark:bg-gray-900
            border border-gray-200 dark:border-gray-700
            rounded shadow-lg
            py-0.5 min-w-[140px]
          "
          role="menu"
        >
          {Object.values(LINE_TYPE_CONFIGS).map((typeConfig: LineTypeConfig) => (
            <button
              key={typeConfig.type}
              onClick={() => handleTypeSelect(typeConfig.type)}
              className={`
                w-full px-2 py-1 flex items-center gap-2
                text-left text-xs
                hover:bg-gray-100 dark:hover:bg-gray-800
                ${typeConfig.type === lineType ? 'bg-gray-50 dark:bg-gray-800' : ''}
              `}
              role="menuitem"
            >
              <span className="w-4 text-center">{typeConfig.icon}</span>
              <span className="flex-1">{typeConfig.label}</span>
              {typeConfig.prefix && (
                <code className="text-[10px] text-gray-400 bg-gray-100 dark:bg-gray-800 px-0.5 rounded">
                  {typeConfig.prefix}
                </code>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
