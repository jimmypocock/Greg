'use client';

import { use, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useSong, useDeleteSong, useSuggestStructure, useApplyStructure, songKeys } from '@/hooks/queries/songs';
import { useYjsSongData } from '@/hooks/useYjsSongData';
import { useQueryClient } from '@tanstack/react-query';
import { ThreePaneLayout } from '@/components/layout/ThreePaneLayout';
import { ToolboxPanel } from '@/components/toolbox/ToolboxPanel';
import { CanvasPanel } from '@/components/canvas';
import { ChatPanel } from '@/components/chat/ChatPanel';
import { SongStatus, StructureSuggestion } from '@/types';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { UserMenu } from '@/components/auth/UserMenu';
import { ShareButton } from '@/components/collaboration/ShareButton';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function SongPage({ params }: PageProps) {
  return (
    <AuthGuard>
      <SongPageContent params={params} />
    </AuthGuard>
  );
}

function SongPageContent({ params }: PageProps) {
  const resolvedParams = use(params);
  const router = useRouter();
  const queryClient = useQueryClient();

  // REST API for initial load and features not yet on Yjs
  const { data: initialSong, isLoading: restLoading, error: restError } = useSong(resolvedParams.id);
  const deleteSongMutation = useDeleteSong();
  const suggestStructure = useSuggestStructure(resolvedParams.id);
  const applyStructure = useApplyStructure(resolvedParams.id);

  // Yjs for song metadata (title, key, tempo, etc.)
  const {
    song,
    updateMeta: yjsUpdateMeta,
  } = useYjsSongData({
    songId: resolvedParams.id,
    initialSong: initialSong || null,
    autoConnect: true,
  });

  const isLoading = restLoading;
  const error = restError;

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [suggestion, setSuggestion] = useState<StructureSuggestion | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(true);
  const [canvasStatus, setCanvasStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
  const [canvasConnectedUsers, setCanvasConnectedUsers] = useState(0);

  // Connection status callback from CanvasPanel
  const handleConnectionStatusChange = useCallback((status: 'disconnected' | 'connecting' | 'connected' | 'error', connectedUsers: number) => {
    setCanvasStatus(status);
    setCanvasConnectedUsers(connectedUsers);
  }, []);

  // Metadata updates (used by ToolboxPanel)
  const handleUpdateSong = async (data: { title?: string; key?: string; tempo?: number; time_signature?: string; status?: SongStatus; notes?: string }) => {
    yjsUpdateMeta(data);
  };

  // Refresh song data when AI updates it
  const handleSongUpdated = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: songKeys.detail(resolvedParams.id) });
  }, [queryClient, resolvedParams.id]);

  const handleDelete = async () => {
    await deleteSongMutation.mutateAsync(resolvedParams.id);
    router.push('/');
  };

  const handleSuggestStructure = async () => {
    const result = await suggestStructure.mutateAsync();
    setSuggestion(result);
  };

  const handleApplyStructure = async () => {
    if (suggestion) {
      await applyStructure.mutateAsync({ sections: suggestion.sections });
      setSuggestion(null);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">Loading song...</p>
        </div>
      </div>
    );
  }

  if (error || !song) {
    return (
      <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
        <div className="max-w-2xl mx-auto px-4 py-16">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h3 className="text-lg font-medium text-red-800 dark:text-red-200">Error loading song</h3>
            <p className="mt-2 text-sm text-red-700 dark:text-red-300">
              {error instanceof Error ? error.message : 'Song not found'}
            </p>
            <Link
              href="/"
              className="mt-4 inline-flex items-center text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-500"
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to songs
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-100 dark:bg-gray-900 flex flex-col overflow-hidden">
      {/* Header */}
      <header className="flex-shrink-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 no-print">
        <div className="px-4 py-3 flex items-center justify-between">
          <Link
            href="/dashboard"
            className="text-sm font-semibold text-gray-900 dark:text-white hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
          >
            Greg
          </Link>
          <div className="flex items-center gap-2">
            {/* Connection Status */}
            <div className="flex items-center border-r border-gray-200 pr-2 mr-2">
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-2 h-2 rounded-full ${
                    canvasStatus === 'connected'
                      ? 'bg-green-500'
                      : canvasStatus === 'connecting'
                      ? 'bg-yellow-500 animate-pulse'
                      : canvasStatus === 'error'
                      ? 'bg-red-500'
                      : 'bg-gray-400'
                  }`}
                />
                {canvasConnectedUsers > 1 && (
                  <span className="text-xs text-gray-500">{canvasConnectedUsers}</span>
                )}
              </div>
            </div>
            {/* AI Assistant toggle */}
            <button
              onClick={() => setAiPanelOpen(!aiPanelOpen)}
              className={`
                p-1.5 rounded transition-colors
                ${aiPanelOpen
                  ? 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/30'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
                }
              `}
              title={aiPanelOpen ? 'Hide AI Assistant' : 'Show AI Assistant'}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </button>
            <ShareButton songId={resolvedParams.id} songTitle={song.title} />
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              Delete
            </button>
            <UserMenu />
          </div>
        </div>
      </header>

      {/* Structure Suggestion Banner */}
      {song.raw_input && song.sections.length === 0 && !suggestion && (
        <div className="flex-shrink-0 bg-indigo-50 dark:bg-indigo-900/20 border-b border-indigo-200 dark:border-indigo-800 px-4 py-3 no-print">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-indigo-800 dark:text-indigo-200">
                Unstructured lyrics detected
              </p>
              <p className="text-xs text-indigo-600 dark:text-indigo-300 mt-0.5">
                Let AI analyze and suggest a song structure
              </p>
            </div>
            <button
              onClick={handleSuggestStructure}
              disabled={suggestStructure.isPending}
              className="px-4 py-2 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              {suggestStructure.isPending ? 'Analyzing...' : 'Suggest Structure'}
            </button>
          </div>
        </div>
      )}

      {/* Structure Suggestion Modal */}
      {suggestion && (
        <div className="flex-shrink-0 bg-green-50 dark:bg-green-900/20 border-b border-green-200 dark:border-green-800 px-4 py-3 no-print">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-green-800 dark:text-green-200">
                Structure Suggestion ({Math.round(suggestion.confidence * 100)}% confidence)
              </p>
              {suggestion.reasoning && (
                <p className="text-xs text-green-600 dark:text-green-300 mt-1">
                  {suggestion.reasoning}
                </p>
              )}
              <div className="flex flex-wrap gap-2 mt-2">
                {suggestion.sections.map((section, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 text-xs bg-white dark:bg-gray-800 rounded border border-green-200 dark:border-green-700 text-green-700 dark:text-green-300"
                  >
                    {section.type}
                    {section.number && ` ${section.number}`}
                    <span className="text-green-500 dark:text-green-400 ml-1">
                      ({section.lines.length})
                    </span>
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2 ml-4">
              <button
                onClick={() => setSuggestion(null)}
                className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Dismiss
              </button>
              <button
                onClick={handleApplyStructure}
                disabled={applyStructure.isPending}
                className="px-4 py-1.5 text-sm font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {applyStructure.isPending ? 'Applying...' : 'Apply'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Three Pane Layout - AI on left, Editor in center, Data on right */}
      <ThreePaneLayout
        leftPanel={
          <ChatPanel
            song={song}
            onSongUpdated={handleSongUpdated}
          />
        }
        centerPanel={
          <CanvasPanel
            songId={resolvedParams.id}
            song={song}
            onConnectionStatusChange={handleConnectionStatusChange}
          />
        }
        rightPanel={
          <ToolboxPanel
            song={song}
            onUpdateSong={handleUpdateSong}
            isUpdating={false}
          />
        }
        leftPanelOpen={aiPanelOpen}
        onLeftPanelToggle={setAiPanelOpen}
      />

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 no-print">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl p-6 max-w-sm mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Delete Song
            </h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Are you sure you want to delete &quot;{song.title}&quot;? This action cannot be undone.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteSongMutation.isPending}
                className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {deleteSongMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
