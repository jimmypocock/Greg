'use client';

import { Song, SongUpdateRequest, SectionType } from '@/types';
import { CollapsibleSection } from '@/components/layout/CollapsibleSection';
import { MetadataEditor } from './MetadataEditor';
import { SectionNavigator } from './SectionNavigator';
import { ConversationHistoryTool } from './AICriticTool';
import { SongNotes } from '@/components/SongNotes';

interface ToolboxPanelProps {
  song: Song;
  selectedSectionId: string | null;
  onSelectSection: (sectionId: string | null) => void;
  onUpdateSong: (data: SongUpdateRequest) => Promise<void>;
  onUpdateLine: (sectionId: string, lineId: string, text: string) => Promise<void>;
  onAddLine: (sectionId: string) => Promise<void>;
  onAddLineWithText: (sectionId: string, text: string) => Promise<void>;
  onDeleteLine: (sectionId: string, lineId: string) => Promise<void>;
  onDeleteSection: (sectionId: string) => Promise<void>;
  onUpdateSection: (sectionId: string, type: SectionType) => Promise<void>;
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
  onUpdateSection,
  onReorderSections,
  onReorderLines,
  onAddSection,
  isUpdating,
  isMutating,
  onAddLineWithText,
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
          onAddLineWithText={onAddLineWithText}
          onDeleteLine={onDeleteLine}
          onDeleteSection={onDeleteSection}
          onUpdateSection={onUpdateSection}
          onAddSection={onAddSection}
          isMutating={isMutating}
        />
      </CollapsibleSection>

      {/* Conversations - AI chat history */}
      <CollapsibleSection
        title="Conversations"
        storageKey="conversations"
        defaultExpanded={false}
        icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        }
      >
        <ConversationHistoryTool songId={song.id} />
      </CollapsibleSection>

      {/* Notes - simple brain dump */}
      <CollapsibleSection
        title="Notes"
        storageKey="notes"
        defaultExpanded={false}
        icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        }
      >
        <SongNotes song={song} onUpdate={onUpdateSong} />
      </CollapsibleSection>
    </div>
  );
}
