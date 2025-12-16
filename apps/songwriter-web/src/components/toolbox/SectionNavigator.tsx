'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Section, SectionType, Line } from '@/types';

interface SectionNavigatorProps {
  sections: Section[];
  selectedSectionId: string | null;
  onSelectSection: (sectionId: string | null) => void;
  onReorderSections: (sectionIds: string[]) => void;
  onReorderLines: (sectionId: string, lineIds: string[]) => void;
  onUpdateLine: (sectionId: string, lineId: string, text: string) => void;
  onAddLine: (sectionId: string) => void;
  onDeleteLine: (sectionId: string, lineId: string) => void;
  onDeleteSection: (sectionId: string) => void;
  onAddSection?: () => void;
  isMutating?: boolean;
}

const sectionLabels: Record<SectionType, string> = {
  [SectionType.INTRO]: 'Intro',
  [SectionType.VERSE]: 'Verse',
  [SectionType.PRE_CHORUS]: 'Pre-Chorus',
  [SectionType.CHORUS]: 'Chorus',
  [SectionType.POST_CHORUS]: 'Post-Chorus',
  [SectionType.BRIDGE]: 'Bridge',
  [SectionType.OUTRO]: 'Outro',
  [SectionType.INSTRUMENTAL]: 'Instrumental',
  [SectionType.SOLO]: 'Solo',
  [SectionType.BREAKDOWN]: 'Breakdown',
  [SectionType.OTHER]: 'Other',
};

const sectionColors: Record<SectionType, string> = {
  [SectionType.INTRO]: 'border-l-gray-400',
  [SectionType.VERSE]: 'border-l-blue-500',
  [SectionType.PRE_CHORUS]: 'border-l-purple-400',
  [SectionType.CHORUS]: 'border-l-indigo-500',
  [SectionType.POST_CHORUS]: 'border-l-purple-500',
  [SectionType.BRIDGE]: 'border-l-amber-500',
  [SectionType.OUTRO]: 'border-l-gray-500',
  [SectionType.INSTRUMENTAL]: 'border-l-teal-500',
  [SectionType.SOLO]: 'border-l-pink-500',
  [SectionType.BREAKDOWN]: 'border-l-red-500',
  [SectionType.OTHER]: 'border-l-gray-400',
};

// Sortable Line Component
interface SortableLineProps {
  line: { id: string; text: string };
  isEditing: boolean;
  editText: string;
  onStartEdit: () => void;
  onEditChange: (text: string) => void;
  onSaveEdit: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  onDelete: () => void;
  isMutating?: boolean;
}

function SortableLine({
  line,
  isEditing,
  editText,
  onStartEdit,
  onEditChange,
  onSaveEdit,
  onKeyDown,
  onDelete,
  isMutating,
}: SortableLineProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: line.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`group flex items-start gap-1 ${isDragging ? 'opacity-50' : ''}`}
    >
      {isEditing ? (
        <input
          type="text"
          value={editText}
          onChange={(e) => onEditChange(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={onSaveEdit}
          autoFocus
          className="
            flex-1 px-2 py-1 text-xs font-mono
            bg-white dark:bg-gray-900
            border border-indigo-300 dark:border-indigo-600
            rounded
            focus:outline-none focus:ring-1 focus:ring-indigo-500
          "
        />
      ) : (
        <>
          {/* Line Drag Handle */}
          <div
            {...attributes}
            {...listeners}
            className="cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 p-1"
            onClick={(e) => e.stopPropagation()}
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
            </svg>
          </div>
          <div
            onClick={onStartEdit}
            className="
              flex-1 px-2 py-1 text-xs font-mono
              text-gray-700 dark:text-gray-300
              hover:bg-gray-50 dark:hover:bg-gray-750
              rounded cursor-text truncate
            "
            title={line.text || '(empty)'}
          >
            {line.text || <span className="text-gray-400 italic">(empty)</span>}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (!isMutating) {
                onDelete();
              }
            }}
            disabled={isMutating}
            className={`
              opacity-0 group-hover:opacity-100
              p-1 text-gray-400 hover:text-red-500
              transition-opacity cursor-pointer
              ${isMutating ? 'cursor-not-allowed opacity-50' : ''}
            `}
            title="Delete line"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </>
      )}
    </div>
  );
}

interface SortableSectionProps {
  section: Section;
  lines: Line[]; // Optimistic lines state
  isExpanded: boolean;
  onToggle: () => void;
  onUpdateLine: (lineId: string, text: string) => void;
  onAddLine: () => void;
  onDeleteLine: (lineId: string) => void;
  onDeleteSection: () => void;
  onReorderLines: (lineIds: string[], newLines: Line[]) => void;
  isMutating?: boolean;
}

function SortableSection({
  section,
  lines,
  isExpanded,
  onToggle,
  onUpdateLine,
  onAddLine,
  onDeleteLine,
  onDeleteSection,
  onReorderLines,
  isMutating,
}: SortableSectionProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: section.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const [editingLineId, setEditingLineId] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  // Sensors for line drag and drop
  const lineSensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleLineDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = lines.findIndex((l) => l.id === active.id);
      const newIndex = lines.findIndex((l) => l.id === over.id);
      const newLines = arrayMove(lines, oldIndex, newIndex);
      onReorderLines(newLines.map((l) => l.id), newLines);
    }
  };

  const label = sectionLabels[section.type] || section.type;
  const fullLabel = section.number ? `${label} ${section.number}` : label;

  const handleStartEdit = (lineId: string, currentText: string) => {
    setEditingLineId(lineId);
    setEditText(currentText);
  };

  const handleSaveEdit = () => {
    if (editingLineId) {
      onUpdateLine(editingLineId, editText);
    }
    setEditingLineId(null);
    setEditText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSaveEdit();
    } else if (e.key === 'Escape') {
      setEditingLineId(null);
      setEditText('');
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`
        border-l-4 ${sectionColors[section.type]}
        bg-white dark:bg-gray-800
        rounded-r-lg
        transition-all duration-150
        ${isDragging ? 'opacity-50 shadow-lg z-10' : ''}
      `}
    >
      {/* Section Header */}
      <div
        className="group/header flex items-center px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-750"
        onClick={onToggle}
      >
        {/* Drag Handle */}
        <div
          {...attributes}
          {...listeners}
          className="mr-2 cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600"
          onClick={(e) => e.stopPropagation()}
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
          </svg>
        </div>

        <div className="flex-1">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
            {fullLabel}
          </span>
          <span className="ml-2 text-xs text-gray-400">
            {lines.length} {lines.length === 1 ? 'line' : 'lines'}
          </span>
        </div>

        {/* Delete Section Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (!isMutating) {
              onDeleteSection();
            }
          }}
          disabled={isMutating}
          className={`
            opacity-0 group-hover/header:opacity-100
            p-1 mr-1 text-gray-400 hover:text-red-500
            transition-opacity cursor-pointer
            ${isMutating ? 'cursor-not-allowed opacity-50' : ''}
          `}
          title="Delete section"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>

        <svg
          className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {/* Expanded Content - Line Editor with Drag & Drop */}
      {isExpanded && (
        <div className="px-3 pb-3 border-t border-gray-100 dark:border-gray-700">
          <div className="mt-2 space-y-1">
            {lines.length === 0 ? (
              <p className="text-xs text-gray-400 italic py-2">No lines yet</p>
            ) : (
              <DndContext
                sensors={lineSensors}
                collisionDetection={closestCenter}
                onDragEnd={handleLineDragEnd}
              >
                <SortableContext
                  items={lines.map((l) => l.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {lines.map((line) => (
                    <SortableLine
                      key={line.id}
                      line={line}
                      isEditing={editingLineId === line.id}
                      editText={editText}
                      onStartEdit={() => handleStartEdit(line.id, line.text)}
                      onEditChange={setEditText}
                      onSaveEdit={handleSaveEdit}
                      onKeyDown={handleKeyDown}
                      onDelete={() => onDeleteLine(line.id)}
                      isMutating={isMutating}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            )}
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (!isMutating) {
                onAddLine();
              }
            }}
            disabled={isMutating}
            className={`
              mt-2 w-full py-1.5 text-xs
              text-indigo-600 dark:text-indigo-400
              hover:bg-indigo-50 dark:hover:bg-indigo-900/20
              rounded transition-colors
              ${isMutating ? 'cursor-not-allowed opacity-50' : ''}
            `}
          >
            {isMutating ? 'Working...' : '+ Add Line'}
          </button>
        </div>
      )}
    </div>
  );
}

export function SectionNavigator({
  sections,
  selectedSectionId,
  onSelectSection,
  onReorderSections,
  onReorderLines,
  onUpdateLine,
  onAddLine,
  onDeleteLine,
  onDeleteSection,
  onAddSection,
  isMutating,
}: SectionNavigatorProps) {
  // Local optimistic state for sections order
  const [localSections, setLocalSections] = useState<Section[]>(sections);

  // Local optimistic state for lines order per section
  const [localLinesMap, setLocalLinesMap] = useState<Record<string, Line[]>>(() => {
    const map: Record<string, Line[]> = {};
    sections.forEach(s => { map[s.id] = s.lines; });
    return map;
  });

  // Sync local state with props when sections change from server
  // Use a key based on section IDs and line IDs to detect real changes
  const sectionsKey = useMemo(() => {
    return sections.map(s => `${s.id}:${s.lines.map(l => l.id).join(',')}`).join('|');
  }, [sections]);

  useEffect(() => {
    setLocalSections(sections);
    const map: Record<string, Line[]> = {};
    sections.forEach(s => { map[s.id] = s.lines; });
    setLocalLinesMap(map);
  }, [sectionsKey]);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = localSections.findIndex((s) => s.id === active.id);
      const newIndex = localSections.findIndex((s) => s.id === over.id);
      const newOrder = arrayMove(localSections, oldIndex, newIndex);

      // Optimistically update local state immediately
      setLocalSections(newOrder);

      // Then trigger the server update
      onReorderSections(newOrder.map((s) => s.id));
    }
  };

  const handleReorderLines = (sectionId: string, lineIds: string[], newLines: Line[]) => {
    // Optimistically update local state immediately
    setLocalLinesMap(prev => ({
      ...prev,
      [sectionId]: newLines,
    }));

    // Then trigger the server update
    onReorderLines(sectionId, lineIds);
  };

  if (sections.length === 0) {
    return (
      <div className="text-center py-6">
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
          No sections yet
        </p>
        {onAddSection && (
          <button
            onClick={onAddSection}
            className="
              px-4 py-2 text-sm font-medium
              bg-indigo-600 text-white
              rounded-lg hover:bg-indigo-700
              transition-colors
            "
          >
            + Add Section
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={localSections.map((s) => s.id)}
          strategy={verticalListSortingStrategy}
        >
          {localSections.map((section) => (
            <SortableSection
              key={section.id}
              section={section}
              lines={localLinesMap[section.id] || section.lines}
              isExpanded={section.id === selectedSectionId}
              onToggle={() => onSelectSection(section.id === selectedSectionId ? null : section.id)}
              onUpdateLine={(lineId, text) => onUpdateLine(section.id, lineId, text)}
              onAddLine={() => onAddLine(section.id)}
              onDeleteLine={(lineId) => onDeleteLine(section.id, lineId)}
              onDeleteSection={() => onDeleteSection(section.id)}
              onReorderLines={(lineIds, newLines) => handleReorderLines(section.id, lineIds, newLines)}
              isMutating={isMutating}
            />
          ))}
        </SortableContext>
      </DndContext>

      {onAddSection && (
        <button
          onClick={onAddSection}
          className="
            w-full py-2 text-sm
            text-indigo-600 dark:text-indigo-400
            hover:bg-indigo-50 dark:hover:bg-indigo-900/20
            rounded-lg transition-colors
          "
        >
          + Add Section
        </button>
      )}
    </div>
  );
}
