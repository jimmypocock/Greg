'use client';

import { useState } from 'react';
import { Section } from '@/types';
import { sectionLabels } from '@/lib/constants';

interface SectionEditorProps {
  section: Section;
  onUpdateLine?: (sectionId: string, lineId: string, text: string) => void;
  onAddLine?: (sectionId: string) => void;
}

export function SectionEditor({ section, onUpdateLine, onAddLine }: SectionEditorProps) {
  const [editingLineId, setEditingLineId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const label = sectionLabels[section.type] || section.type;
  const fullLabel = section.number ? `${label} ${section.number}` : label;

  const handleStartEdit = (lineId: string, currentText: string) => {
    setEditingLineId(lineId);
    setEditText(currentText);
  };

  const handleSaveEdit = () => {
    if (editingLineId && onUpdateLine) {
      onUpdateLine(section.id, editingLineId, editText);
    }
    setEditingLineId(null);
    setEditText('');
  };

  const handleCancelEdit = () => {
    setEditingLineId(null);
    setEditText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      handleCancelEdit();
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">{fullLabel}</h3>
        {onAddLine && (
          <button
            onClick={() => onAddLine(section.id)}
            className="text-xs text-indigo-600 hover:text-indigo-800"
          >
            + Add line
          </button>
        )}
      </div>
      <div className="p-4 space-y-1 font-mono text-sm">
        {section.lines.length === 0 ? (
          <p className="text-gray-400 italic">No lyrics in this section</p>
        ) : (
          section.lines.map((line) => (
            <div key={line.id} className="group">
              {line.chords.length > 0 && (
                <div className="text-indigo-600 font-medium">
                  {renderChordLine(line.text, line.chords)}
                </div>
              )}
              {editingLineId === line.id ? (
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onBlur={handleSaveEdit}
                    autoFocus
                    className="flex-1 px-2 py-1 border border-indigo-300 rounded text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              ) : (
                <div
                  onClick={() => handleStartEdit(line.id, line.text)}
                  className="cursor-pointer hover:bg-gray-50 px-1 -mx-1 rounded transition-colors"
                  title="Click to edit"
                >
                  {line.text || <span className="text-gray-300">(empty line)</span>}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function renderChordLine(text: string, chords: { chord: string; position: number }[]): string {
  const sortedChords = [...chords].sort((a, b) => a.position - b.position);
  const chordLine = Array(Math.max(text.length, 1)).fill(' ');

  for (const { chord, position } of sortedChords) {
    for (let i = 0; i < chord.length; i++) {
      const pos = position + i;
      if (pos < chordLine.length) {
        chordLine[pos] = chord[i];
      } else {
        chordLine.push(chord[i]);
      }
    }
  }

  return chordLine.join('').trimEnd();
}
