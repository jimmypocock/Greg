'use client';

/**
 * Canvas Panel - Center panel for song editing.
 *
 * Manages its own Yjs connection and ProseMirror editor.
 * Handles version management and audio uploads internally.
 */

import { useCallback, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Song } from '@/types';
import { Canvas } from './Canvas';
import { useYjsProseMirror } from '@/hooks/useYjsProseMirror';
import { useUploadAudio } from '@/hooks/queries/audio';
import { duplicateVersion, promoteVersion } from '@/lib/versions';
import { songKeys } from '@/hooks/queries/songs';

interface CanvasPanelProps {
  songId: string;
  song: Song;
  onConnectionStatusChange?: (status: 'disconnected' | 'connecting' | 'connected' | 'error', connectedUsers: number) => void;
}

export function CanvasPanel({
  songId,
  song,
  onConnectionStatusChange,
}: CanvasPanelProps) {
  const queryClient = useQueryClient();
  const uploadAudio = useUploadAudio(songId);

  // Yjs connection for real-time collaboration
  const {
    yXmlFragment,
    provider,
    status,
    connectedUsers,
  } = useYjsProseMirror({
    songId,
    autoConnect: true,
  });

  // Notify parent of connection status changes
  useEffect(() => {
    onConnectionStatusChange?.(status, connectedUsers);
  }, [status, connectedUsers, onConnectionStatusChange]);

  // Version handlers
  const handleDuplicateVersion = useCallback(async (sectionId: string, versionId: string) => {
    const newVersion = await duplicateVersion(songId, sectionId, versionId);
    await promoteVersion(songId, sectionId, newVersion.id);
    queryClient.invalidateQueries({ queryKey: songKeys.detail(songId) });
  }, [songId, queryClient]);

  const handleSwitchVersion = useCallback(async (sectionId: string, versionId: string) => {
    await promoteVersion(songId, sectionId, versionId);
    queryClient.invalidateQueries({ queryKey: songKeys.detail(songId) });
  }, [songId, queryClient]);

  const handleUploadAudio = useCallback(async (sectionId: string, versionId: string, file: File) => {
    await uploadAudio.mutateAsync({
      file,
      isReference: false,
      sectionVersionId: versionId,
    });
  }, [uploadAudio]);

  const handleReorderParts = useCallback(async (partIds: string[]) => {
    // TODO: Implement when ProseMirror supports part reordering
    console.log('Reorder parts:', partIds);
  }, []);

  // Don't render Canvas until Yjs is synced - prevents the "create non-collaborative,
  // then destroy and recreate collaborative" dance that was causing content to disappear
  if (!yXmlFragment || !provider) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-2"></div>
          <p className="text-sm">Connecting...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto">
      <Canvas
        song={song}
        yXmlFragment={yXmlFragment}
        provider={provider}
        onDuplicateVersion={handleDuplicateVersion}
        onSwitchVersion={handleSwitchVersion}
        onUploadAudio={handleUploadAudio}
        onReorderParts={handleReorderParts}
      />
    </div>
  );
}
