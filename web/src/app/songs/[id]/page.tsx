'use client';

import { use, useState, useCallback, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useSong, useDeleteSong, useSuggestStructure, useApplyStructure, useSaveCanvas, songKeys } from '@/hooks/queries/songs';
import { useYjsSongData } from '@/hooks/useYjsSongData';
import { useYjsCanvas } from '@/hooks/useYjsCanvas';
import { duplicateVersion, promoteVersion } from '@/lib/versions';
import { useUploadAudio } from '@/hooks/queries/audio';
import { useQueryClient } from '@tanstack/react-query';
import { ThreePaneLayout } from '@/components/layout/ThreePaneLayout';
import { ToolboxPanel } from '@/components/toolbox/ToolboxPanel';
import { LivePreviewPanel } from '@/components/preview/LivePreviewPanel';
import { CodeMirrorCanvas, toApiFormat } from '@/components/canvas';
import { AIChatPanel } from '@/components/chat/AIChatPanel';
import { SongStatus, StructureSuggestion, SectionType } from '@/types';
import { useUndoRedo } from '@/hooks/useUndoRedo';
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

  // Editor mode - defined early so hooks can use it
  const [editorMode, setEditorMode] = useState<'sections' | 'canvas'>('canvas');

  // REST API for initial load and features not yet on Yjs
  const { data: initialSong, isLoading: restLoading, error: restError } = useSong(resolvedParams.id);
  const deleteSongMutation = useDeleteSong();
  const suggestStructure = useSuggestStructure(resolvedParams.id);
  const applyStructure = useApplyStructure(resolvedParams.id);
  const uploadAudio = useUploadAudio(resolvedParams.id);
  const saveCanvasMutation = useSaveCanvas(resolvedParams.id);

  // Yjs for real-time collaborative editing (sections view)
  // Only connect when in sections mode to avoid conflicting connections
  const {
    song,
    isLoading: yjsLoading,
    status: yjsStatus,
    connectedUsers,
    updateLine: yjsUpdateLine,
    addLine: yjsAddLine,
    deleteLine: yjsDeleteLine,
    addSection: yjsAddSection,
    deleteSection: yjsDeleteSection,
    updateSection: yjsUpdateSection,
    updateMeta: yjsUpdateMeta,
    addChord: yjsAddChord,
    removeChord: yjsRemoveChord,
    reorderSections: yjsReorderSections,
    reorderLines: yjsReorderLines,
  } = useYjsSongData({
    songId: resolvedParams.id,
    initialSong: initialSong || null,
    autoConnect: editorMode === 'sections',
  });

  // Yjs for canvas (real-time text editing)
  // Only connect when in canvas mode
  const {
    yText,
    provider: canvasProvider,
    status: canvasStatus,
    isSynced: canvasSynced,
    connectedUsers: canvasConnectedUsers,
  } = useYjsCanvas({
    songId: resolvedParams.id,
    autoConnect: editorMode === 'canvas',
  });

  const isLoading = restLoading || (editorMode === 'sections' && yjsLoading);
  const error = restError;

  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [suggestion, setSuggestion] = useState<StructureSuggestion | null>(null);
  const [aiPanelOpen, setAiPanelOpen] = useState(true);
  const [focusLineId, setFocusLineId] = useState<string | null>(null);
  const [focusCursorPosition, setFocusCursorPosition] = useState<number>(0);
  const [showChords, setShowChords] = useState(true);

  // Use canvas connection status when in canvas mode
  const effectiveStatus = editorMode === 'canvas' ? canvasStatus : yjsStatus;
  const effectiveConnectedUsers = editorMode === 'canvas' ? canvasConnectedUsers : connectedUsers;

  // Undo/Redo support
  const { pushAction, undo, redo, canUndo, canRedo, isPerformingAction } = useUndoRedo();

  // Keep a ref to the latest song state for use in undo/redo callbacks
  // This avoids stale closures when callbacks execute later
  const songRef = useRef(song);
  useEffect(() => {
    songRef.current = song;
  }, [song]);

  // Version handlers
  const handleDuplicateVersion = useCallback(async (sectionId: string, versionId: string) => {
    // Duplicate the version
    const newVersion = await duplicateVersion(resolvedParams.id, sectionId, versionId);
    // Promote the new version to main so it displays immediately
    await promoteVersion(resolvedParams.id, sectionId, newVersion.id);
    // Invalidate song query to refresh versions list
    queryClient.invalidateQueries({ queryKey: songKeys.detail(resolvedParams.id) });
  }, [resolvedParams.id, queryClient]);

  // Switch version = promote it to main so it displays everywhere
  const handleSwitchVersion = useCallback(async (sectionId: string, versionId: string) => {
    await promoteVersion(resolvedParams.id, sectionId, versionId);
    // Invalidate song query to refresh with new main version's lines
    queryClient.invalidateQueries({ queryKey: songKeys.detail(resolvedParams.id) });
  }, [resolvedParams.id, queryClient]);

  // Upload audio file for a specific version
  const handleUploadVersionAudio = useCallback(async (sectionId: string, versionId: string, file: File) => {
    await uploadAudio.mutateAsync({
      file,
      isReference: false,
      sectionVersionId: versionId,
    });
  }, [uploadAudio]);

  // Add chord to a line
  const handleAddChord = useCallback((sectionId: string, lineId: string, chord: string, position: number) => {
    yjsAddChord(sectionId, lineId, chord, position);
  }, [yjsAddChord]);

  // Remove chord from a line
  const handleRemoveChord = useCallback((sectionId: string, lineId: string, position: number) => {
    yjsRemoveChord(sectionId, lineId, position);
  }, [yjsRemoveChord]);

  const handleUpdateSong = async (data: { title?: string; key?: string; tempo?: number; time_signature?: string; status?: SongStatus; notes?: string }) => {
    yjsUpdateMeta(data);
  };

  const handleUpdateLine = useCallback((sectionId: string, lineId: string, text: string) => {
    // Find the current line text for undo
    const section = song?.sections.find(s => s.id === sectionId);
    const line = section?.lines.find(l => l.id === lineId);
    const previousText = line?.text || '';

    yjsUpdateLine(sectionId, lineId, text);

    // Only push to undo if text actually changed
    if (previousText !== text) {
      pushAction({
        description: 'Edit line',
        undo: async () => {
          yjsUpdateLine(sectionId, lineId, previousText);
        },
        redo: async () => {
          yjsUpdateLine(sectionId, lineId, text);
        },
      });
    }
  }, [song, yjsUpdateLine, pushAction]);

  const handleAddLine = useCallback((sectionId: string) => {
    const newLineId = yjsAddLine(sectionId, '');

    if (newLineId) {
      pushAction({
        description: 'Add line',
        undo: async () => {
          yjsDeleteLine(sectionId, newLineId);
        },
        redo: async () => {
          yjsAddLine(sectionId, '');
        },
      });
    }
  }, [yjsAddLine, yjsDeleteLine, pushAction]);

  const handleAddLineWithText = useCallback((sectionId: string, text: string) => {
    const newLineId = yjsAddLine(sectionId, text);

    if (newLineId) {
      pushAction({
        description: 'Add line',
        undo: async () => {
          yjsDeleteLine(sectionId, newLineId);
        },
        redo: async () => {
          yjsAddLine(sectionId, text);
        },
      });
    }
  }, [yjsAddLine, yjsDeleteLine, pushAction]);

  // Add line after a specific line (for Enter key handling)
  const handleAddLineAfter = useCallback(async (sectionId: string, afterLineId: string, text: string): Promise<string | undefined> => {
    const newLineId = yjsAddLine(sectionId, text, afterLineId);

    if (newLineId) {
      // Set focus to the new line at position 0
      setFocusLineId(newLineId);
      setFocusCursorPosition(0);

      pushAction({
        description: 'Add line',
        undo: async () => {
          yjsDeleteLine(sectionId, newLineId);
        },
        redo: async () => {
          yjsAddLine(sectionId, text, afterLineId);
        },
      });

      return newLineId;
    }

    return undefined;
  }, [yjsAddLine, yjsDeleteLine, pushAction]);

  // Clear focus after it's been handled
  const handleFocusHandled = useCallback(() => {
    setFocusLineId(null);
    setFocusCursorPosition(0);
  }, []);

  // Toggle chords visibility
  const handleToggleChords = useCallback(() => {
    setShowChords(prev => !prev);
  }, []);

  // Refresh song data when AI shaper updates it
  const handleSongUpdated = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: songKeys.detail(resolvedParams.id) });
  }, [queryClient, resolvedParams.id]);

  // Merge line with the previous line (backspace at start of line with content)
  const handleMergeWithPrevious = useCallback(async (
    sectionId: string,
    lineId: string,
    lineIndex: number,
    currentText: string
  ): Promise<{ focusLineId: string; cursorPosition: number } | undefined> => {
    const section = song?.sections.find(s => s.id === sectionId);
    if (!section || lineIndex === 0) return undefined;

    const previousLine = section.lines[lineIndex - 1];
    if (!previousLine) return undefined;

    const previousText = previousLine.text;
    const mergedText = previousText + currentText;
    const cursorPosition = previousText.length;

    // Update the previous line with merged text
    yjsUpdateLine(sectionId, previousLine.id, mergedText);
    // Delete the current line
    yjsDeleteLine(sectionId, lineId);

    // Set focus to the previous line at the merge point
    setFocusLineId(previousLine.id);
    setFocusCursorPosition(cursorPosition);

    pushAction({
      description: 'Merge lines',
      undo: async () => {
        yjsUpdateLine(sectionId, previousLine.id, previousText);
        yjsAddLine(sectionId, currentText, previousLine.id);
      },
      redo: async () => {
        // Use songRef.current to get the latest state (avoids stale closure)
        const currentSection = songRef.current?.sections.find(s => s.id === sectionId);
        const restoredLineIndex = currentSection?.lines.findIndex(l => l.id === previousLine.id);
        if (restoredLineIndex !== undefined && restoredLineIndex >= 0 && currentSection) {
          const nextLine = currentSection.lines[restoredLineIndex + 1];
          if (nextLine) {
            yjsUpdateLine(sectionId, previousLine.id, mergedText);
            yjsDeleteLine(sectionId, nextLine.id);
          }
        }
      },
    });

    return { focusLineId: previousLine.id, cursorPosition };
  }, [song, yjsUpdateLine, yjsDeleteLine, yjsAddLine, pushAction]);

  // Add a new section after a specific section
  const handleAddSectionAfter = useCallback(async (afterSectionId: string): Promise<string | undefined> => {
    const newSectionId = yjsAddSection(SectionType.VERSE, afterSectionId);

    if (newSectionId) {
      // Select the new section
      setSelectedSectionId(newSectionId);

      // Note: Focus will be handled when the section renders with its first line
      // We need to wait for the Yjs update to propagate

      pushAction({
        description: 'Add section',
        undo: async () => {
          yjsDeleteSection(newSectionId);
        },
        redo: async () => {
          yjsAddSection(SectionType.VERSE, afterSectionId);
        },
      });

      return newSectionId;
    }

    return undefined;
  }, [yjsAddSection, yjsDeleteSection, pushAction]);

  // Add a new section (uses selected section if available, otherwise adds at end)
  const handleAddSection = useCallback(() => {
    // If a section is selected, add after it
    const afterSectionId = selectedSectionId;

    const newSectionId = yjsAddSection(SectionType.VERSE, afterSectionId || undefined);

    if (newSectionId) {
      // Select the new section
      setSelectedSectionId(newSectionId);

      pushAction({
        description: 'Add section',
        undo: async () => {
          yjsDeleteSection(newSectionId);
        },
        redo: async () => {
          yjsAddSection(SectionType.VERSE, afterSectionId || undefined);
        },
      });
    }
  }, [selectedSectionId, yjsAddSection, yjsDeleteSection, pushAction]);

  const handleUpdateSection = useCallback((sectionId: string, type: SectionType) => {
    // Find the current section type for undo
    const section = song?.sections.find(s => s.id === sectionId);
    const previousType = section?.type || SectionType.VERSE;

    yjsUpdateSection(sectionId, type);

    if (previousType !== type) {
      pushAction({
        description: 'Rename section',
        undo: async () => {
          yjsUpdateSection(sectionId, previousType);
        },
        redo: async () => {
          yjsUpdateSection(sectionId, type);
        },
      });
    }
  }, [song, yjsUpdateSection, pushAction]);

  const handleReorderSections = useCallback(async (sectionIds: string[]) => {
    // Store the previous order for undo
    const previousOrder = song?.sections.map(s => s.id) || [];

    yjsReorderSections(sectionIds);

    pushAction({
      description: 'Reorder sections',
      undo: async () => {
        yjsReorderSections(previousOrder);
      },
      redo: async () => {
        yjsReorderSections(sectionIds);
      },
    });
  }, [song, yjsReorderSections, pushAction]);

  const handleDeleteLine = useCallback((sectionId: string, lineId: string) => {
    // Store the line data for potential restoration
    const section = song?.sections.find(s => s.id === sectionId);
    const line = section?.lines.find(l => l.id === lineId);
    const lineText = line?.text || '';
    const lineIndex = section?.lines.findIndex(l => l.id === lineId) ?? -1;
    const previousLineId = lineIndex > 0 ? section?.lines[lineIndex - 1]?.id : undefined;

    yjsDeleteLine(sectionId, lineId);

    pushAction({
      description: 'Delete line',
      undo: async () => {
        yjsAddLine(sectionId, lineText, previousLineId);
      },
      redo: async () => {
        // For redo, we need to find the line again by looking at current state
        const currentSection = songRef.current?.sections.find(s => s.id === sectionId);
        const restoredLine = currentSection?.lines.find(l => l.text === lineText);
        if (restoredLine) {
          yjsDeleteLine(sectionId, restoredLine.id);
        }
      },
    });
  }, [song, yjsDeleteLine, yjsAddLine, pushAction]);

  const handleDeleteSection = useCallback((sectionId: string) => {
    // Store section data for potential restoration
    const section = song?.sections.find(s => s.id === sectionId);
    const sectionType = section?.type || SectionType.VERSE;
    const sectionIndex = song?.sections.findIndex(s => s.id === sectionId) ?? -1;
    const previousSectionId = sectionIndex > 0 ? song?.sections[sectionIndex - 1]?.id : undefined;

    yjsDeleteSection(sectionId);

    // Clear selection if the deleted section was selected
    if (selectedSectionId === sectionId) {
      setSelectedSectionId(null);
    }

    // Note: Undo for delete section is limited - creates empty section, doesn't restore lines
    pushAction({
      description: 'Delete section',
      undo: async () => {
        yjsAddSection(sectionType, previousSectionId);
      },
      redo: async () => {
        // For redo, we need to find the section again
        const currentSections = songRef.current?.sections;
        const restoredSection = currentSections?.find(s => s.type === sectionType);
        if (restoredSection) {
          yjsDeleteSection(restoredSection.id);
        }
      },
    });
  }, [song, yjsDeleteSection, yjsAddSection, selectedSectionId, pushAction]);

  const handleReorderLines = useCallback((sectionId: string, lineIds: string[]) => {
    // Store the previous order for undo
    const section = song?.sections.find(s => s.id === sectionId);
    const previousOrder = section?.lines.map(l => l.id) || [];

    yjsReorderLines(sectionId, lineIds);

    pushAction({
      description: 'Reorder lines',
      undo: async () => {
        yjsReorderLines(sectionId, previousOrder);
      },
      redo: async () => {
        yjsReorderLines(sectionId, lineIds);
      },
    });
  }, [song, yjsReorderLines, pushAction]);

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
                    effectiveStatus === 'connected'
                      ? 'bg-green-500'
                      : effectiveStatus === 'connecting'
                      ? 'bg-yellow-500 animate-pulse'
                      : effectiveStatus === 'error'
                      ? 'bg-red-500'
                      : 'bg-gray-400'
                  }`}
                />
                {effectiveConnectedUsers > 1 && (
                  <span className="text-xs text-gray-500">{effectiveConnectedUsers}</span>
                )}
              </div>
            </div>
            {/* Editor Mode Toggle */}
            <div className="flex items-center border-r border-gray-200 pr-2 mr-2">
              <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-0.5">
                <button
                  onClick={() => setEditorMode('sections')}
                  className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                    editorMode === 'sections'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  Sections
                </button>
                <button
                  onClick={() => setEditorMode('canvas')}
                  className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
                    editorMode === 'canvas'
                      ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  Canvas
                </button>
              </div>
            </div>
            {/* Undo/Redo buttons */}
            <div className="flex items-center border-r border-gray-200 dark:border-gray-700 pr-2 mr-2">
              <button
                onClick={undo}
                disabled={!canUndo || isPerformingAction}
                className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                title="Undo (Cmd+Z)"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                </svg>
              </button>
              <button
                onClick={redo}
                disabled={!canRedo || isPerformingAction}
                className="p-1.5 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                title="Redo (Cmd+Shift+Z)"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 10h-10a8 8 0 00-8 8v2M21 10l-6 6m6-6l-6-6" />
                </svg>
              </button>
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
          <AIChatPanel
            song={song}
            onSongUpdated={handleSongUpdated}
          />
        }
        centerPanel={
          editorMode === 'canvas' ? (
            <div className="h-full overflow-auto py-4">
              <CodeMirrorCanvas
                song={song}
                // yText is null until Yjs sync completes (prevents cursor position errors)
                yText={yText}
                provider={canvasProvider}
                // In collaborative mode (yText exists), Yjs handles persistence
                // Only use REST API save when NOT in collaborative mode
                onSave={yText ? undefined : (parsed) => {
                  const apiData = toApiFormat(parsed);
                  saveCanvasMutation.mutate(apiData);
                }}
                onDuplicateVersion={handleDuplicateVersion}
                onSwitchVersion={handleSwitchVersion}
                onUploadAudio={handleUploadVersionAudio}
                isUploadingAudio={uploadAudio.isPending}
                onReorderSections={handleReorderSections}
              />
            </div>
          ) : (
            <LivePreviewPanel
              song={song}
              selectedSectionId={selectedSectionId}
              onSectionClick={setSelectedSectionId}
              editable={true}
              showChords={showChords}
              onToggleChords={handleToggleChords}
              onAddChord={handleAddChord}
              onRemoveChord={handleRemoveChord}
              onUpdateLine={handleUpdateLine}
              onAddLineAfter={handleAddLineAfter}
              onDeleteLine={handleDeleteLine}
              onMergeWithPrevious={handleMergeWithPrevious}
              onAddSectionAfter={handleAddSectionAfter}
              onDeleteSection={handleDeleteSection}
              onUpdateSection={handleUpdateSection}
              onReorderSections={handleReorderSections}
              onAddSection={handleAddSection}
              onDuplicateVersion={handleDuplicateVersion}
              onSwitchVersion={handleSwitchVersion}
              onUploadAudio={handleUploadVersionAudio}
              isUploadingAudio={uploadAudio.isPending}
              focusLineId={focusLineId}
              focusCursorPosition={focusCursorPosition}
              onFocusHandled={handleFocusHandled}
            />
          )
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
