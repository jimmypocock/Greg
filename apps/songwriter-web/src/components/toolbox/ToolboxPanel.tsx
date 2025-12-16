'use client';

import { Song, SongUpdateRequest } from '@/types';
import { CollapsibleSection } from '@/components/layout/CollapsibleSection';
import { MetadataEditor } from './MetadataEditor';
import { SectionNavigator } from './SectionNavigator';
import { AICriticTool } from './AICriticTool';
import { SongNotesPanel } from '@/components/SongNotesPanel';

interface ToolboxPanelProps {
  song: Song;
  selectedSectionId: string | null;
  onSelectSection: (sectionId: string | null) => void;
  onUpdateSong: (data: SongUpdateRequest) => Promise<void>;
  onUpdateLine: (sectionId: string, lineId: string, text: string) => Promise<void>;
  onAddLine: (sectionId: string) => Promise<void>;
  onDeleteLine: (sectionId: string, lineId: string) => Promise<void>;
  onDeleteSection: (sectionId: string) => Promise<void>;
  onReorderSections: (sectionIds: string[]) => Promise<void>;
  onReorderLines: (sectionId: string, lineIds: string[]) => Promise<void>;
  onAddSection: () => void;
  isUpdating?: boolean;
  isMutating?: boolean;
}

export function ToolboxPanel({
  song,
  selectedSectionId,
  onSelectSection,
  onUpdateSong,
  onUpdateLine,
  onAddLine,
  onDeleteLine,
  onDeleteSection,
  onReorderSections,
  onReorderLines,
  onAddSection,
  isUpdating,
  isMutating,
}: ToolboxPanelProps) {
  return (
    <div className="h-full flex flex-col overflow-y-auto min-h-0">
      {/* Metadata Section */}
      <CollapsibleSection
        title="Song Info"
        storageKey="metadata"
        defaultExpanded={true}
        icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
          </svg>
        }
      >
        <MetadataEditor
          song={song}
          onUpdate={onUpdateSong}
          isUpdating={isUpdating}
        />
      </CollapsibleSection>

      {/* Sections - with inline editing */}
      <CollapsibleSection
        title="Sections"
        storageKey="sections"
        defaultExpanded={true}
        badge={
          <span className="ml-2 px-2 py-0.5 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
            {song.sections.length}
          </span>
        }
        icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
        }
      >
        <SectionNavigator
          sections={song.sections}
          selectedSectionId={selectedSectionId}
          onSelectSection={onSelectSection}
          onReorderSections={onReorderSections}
          onReorderLines={onReorderLines}
          onUpdateLine={onUpdateLine}
          onAddLine={onAddLine}
          onDeleteLine={onDeleteLine}
          onDeleteSection={onDeleteSection}
          onAddSection={onAddSection}
          isMutating={isMutating}
        />
      </CollapsibleSection>

      {/* AI Critic */}
      <CollapsibleSection
        title="AI Critic"
        storageKey="ai-critic"
        defaultExpanded={false}
        icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        }
      >
        <AICriticTool songId={song.id} hasSections={song.sections.length > 0} />
      </CollapsibleSection>

      {/* Brain Dump Notes */}
      <CollapsibleSection
        title="Brain Dump"
        storageKey="notes"
        defaultExpanded={false}
        icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        }
      >
        <SongNotesPanel songId={song.id} />
      </CollapsibleSection>
    </div>
  );
}
