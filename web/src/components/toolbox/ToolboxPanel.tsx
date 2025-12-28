'use client';

import { Song, SongUpdateRequest } from '@/types';
import { CollapsibleSection } from '@/components/layout/CollapsibleSection';
import { MetadataEditor } from './MetadataEditor';
import { ConversationHistoryTool } from './AICriticTool';
import { SongNotes } from '@/components/SongNotes';
import { AudioFilesPanel } from './AudioFilesPanel';
import { SongShapePanel } from './SongShapePanel';

interface ToolboxPanelProps {
  song: Song;
  onUpdateSong: (data: SongUpdateRequest) => Promise<void>;
  isUpdating?: boolean;
}

export function ToolboxPanel({
  song,
  onUpdateSong,
  isUpdating,
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

      {/* Song Shape - theme, images, arc from AI exploration */}
      <CollapsibleSection
        title="Song Shape"
        storageKey="shape"
        defaultExpanded={true}
        icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        }
      >
        <SongShapePanel song={song} />
      </CollapsibleSection>

      {/* Audio Files - for tempo/key detection */}
      <CollapsibleSection
        title="Audio Files"
        storageKey="audio"
        defaultExpanded={false}
        icon={
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
          </svg>
        }
      >
        <AudioFilesPanel songId={song.id} />
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
