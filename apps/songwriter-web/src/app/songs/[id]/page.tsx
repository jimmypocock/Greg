'use client';

import { use, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useSong, useUpdateSong, useDeleteSong, useSuggestStructure, useApplyStructure, useUpdateLine, useAddLine, useAddSection, useUpdateSection, useReorderSections, useDeleteLine, useDeleteSection, useReorderLines } from '@/lib/hooks';
import { SplitPaneLayout } from '@/components/layout/SplitPaneLayout';
import { ToolboxPanel } from '@/components/toolbox/ToolboxPanel';
import { LivePreviewPanel } from '@/components/preview/LivePreviewPanel';
import { SongStatus, StructureSuggestion, SectionType } from '@/types';
import { useUndoRedo } from '@/hooks/useUndoRedo';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function SongPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const router = useRouter();
  const { data: song, isLoading, error } = useSong(resolvedParams.id);
  const updateSong = useUpdateSong(resolvedParams.id);
  const deleteSong = useDeleteSong();
  const suggestStructure = useSuggestStructure(resolvedParams.id);
  const applyStructure = useApplyStructure(resolvedParams.id);
  const updateLine = useUpdateLine(resolvedParams.id);
  const addLine = useAddLine(resolvedParams.id);
  const addSection = useAddSection(resolvedParams.id);
  const updateSectionMutation = useUpdateSection(resolvedParams.id);
  const reorderSections = useReorderSections(resolvedParams.id);
  const deleteLine = useDeleteLine(resolvedParams.id);
  const deleteSectionMutation = useDeleteSection(resolvedParams.id);
  const reorderLines = useReorderLines(resolvedParams.id);

  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [suggestion, setSuggestion] = useState<StructureSuggestion | null>(null);

  // Undo/Redo support
  const { pushAction, undo, redo, canUndo, canRedo, isPerformingAction } = useUndoRedo();

  const handleUpdateSong = async (data: Parameters<typeof updateSong.mutateAsync>[0]) => {
    await updateSong.mutateAsync(data);
  };

  const handleUpdateLine = useCallback(async (sectionId: string, lineId: string, text: string) => {
    // Find the current line text for undo
    const section = song?.sections.find(s => s.id === sectionId);
    const line = section?.lines.find(l => l.id === lineId);
    const previousText = line?.text || '';

    await updateLine.mutateAsync({ section_id: sectionId, line_id: lineId, text });

    // Only push to undo if text actually changed
    if (previousText !== text) {
      pushAction({
        description: 'Edit line',
        undo: async () => {
          await updateLine.mutateAsync({ section_id: sectionId, line_id: lineId, text: previousText });
        },
        redo: async () => {
          await updateLine.mutateAsync({ section_id: sectionId, line_id: lineId, text });
        },
      });
    }
  }, [song, updateLine, pushAction]);

  const handleAddLine = useCallback(async (sectionId: string) => {
    const result = await addLine.mutateAsync({ section_id: sectionId, text: '' });

    // Find the newly added line (it should be the last one in the section)
    const section = result.sections.find(s => s.id === sectionId);
    const newLine = section?.lines[section.lines.length - 1];

    if (newLine) {
      pushAction({
        description: 'Add line',
        undo: async () => {
          await deleteLine.mutateAsync({ section_id: sectionId, line_id: newLine.id });
        },
        redo: async () => {
          await addLine.mutateAsync({ section_id: sectionId, text: '' });
        },
      });
    }
  }, [addLine, deleteLine, pushAction]);

  const handleAddLineWithText = useCallback(async (sectionId: string, text: string) => {
    const result = await addLine.mutateAsync({ section_id: sectionId, text });

    // Find the newly added line (it should be the last one in the section)
    const section = result.sections.find(s => s.id === sectionId);
    const newLine = section?.lines[section.lines.length - 1];

    if (newLine) {
      pushAction({
        description: 'Add line',
        undo: async () => {
          await deleteLine.mutateAsync({ section_id: sectionId, line_id: newLine.id });
        },
        redo: async () => {
          await addLine.mutateAsync({ section_id: sectionId, text });
        },
      });
    }
  }, [addLine, deleteLine, pushAction]);

  const handleAddSection = useCallback(async () => {
    const result = await addSection.mutateAsync({ type: SectionType.VERSE });

    // Find the newly added section (it should be the last one)
    const newSection = result.sections[result.sections.length - 1];

    if (newSection) {
      pushAction({
        description: 'Add section',
        undo: async () => {
          await deleteSectionMutation.mutateAsync(newSection.id);
        },
        redo: async () => {
          await addSection.mutateAsync({ type: SectionType.VERSE });
        },
      });
    }
  }, [addSection, deleteSectionMutation, pushAction]);

  const handleUpdateSection = useCallback(async (sectionId: string, type: SectionType) => {
    // Find the current section type for undo
    const section = song?.sections.find(s => s.id === sectionId);
    const previousType = section?.type || SectionType.VERSE;

    await updateSectionMutation.mutateAsync({ sectionId, type });

    if (previousType !== type) {
      pushAction({
        description: 'Rename section',
        undo: async () => {
          await updateSectionMutation.mutateAsync({ sectionId, type: previousType });
        },
        redo: async () => {
          await updateSectionMutation.mutateAsync({ sectionId, type });
        },
      });
    }
  }, [song, updateSectionMutation, pushAction]);

  const handleReorderSections = useCallback(async (sectionIds: string[]) => {
    // Store the previous order for undo
    const previousOrder = song?.sections.map(s => s.id) || [];

    await reorderSections.mutateAsync({ section_ids: sectionIds });

    pushAction({
      description: 'Reorder sections',
      undo: async () => {
        await reorderSections.mutateAsync({ section_ids: previousOrder });
      },
      redo: async () => {
        await reorderSections.mutateAsync({ section_ids: sectionIds });
      },
    });
  }, [song, reorderSections, pushAction]);

  const handleDeleteLine = useCallback(async (sectionId: string, lineId: string) => {
    // Store the line data for potential restoration
    const section = song?.sections.find(s => s.id === sectionId);
    const line = section?.lines.find(l => l.id === lineId);
    const lineText = line?.text || '';

    await deleteLine.mutateAsync({ section_id: sectionId, line_id: lineId });

    // Note: Undo for delete is limited - adds line at end, not original position
    pushAction({
      description: 'Delete line',
      undo: async () => {
        await addLine.mutateAsync({ section_id: sectionId, text: lineText });
      },
      redo: async () => {
        // For redo, we can't delete the same line, so we just skip
        // This is a limitation of the current API
      },
    });
  }, [song, deleteLine, addLine, pushAction]);

  const handleDeleteSection = useCallback(async (sectionId: string) => {
    // Store section data for potential restoration
    const section = song?.sections.find(s => s.id === sectionId);
    const sectionType = section?.type || SectionType.VERSE;

    await deleteSectionMutation.mutateAsync(sectionId);

    // Clear selection if the deleted section was selected
    if (selectedSectionId === sectionId) {
      setSelectedSectionId(null);
    }

    // Note: Undo for delete section is limited - creates empty section, doesn't restore lines
    pushAction({
      description: 'Delete section',
      undo: async () => {
        await addSection.mutateAsync({ type: sectionType });
      },
      redo: async () => {
        // For redo, we can't delete the same section
      },
    });
  }, [song, deleteSectionMutation, addSection, selectedSectionId, pushAction]);

  const handleReorderLines = useCallback(async (sectionId: string, lineIds: string[]) => {
    // Store the previous order for undo
    const section = song?.sections.find(s => s.id === sectionId);
    const previousOrder = section?.lines.map(l => l.id) || [];

    await reorderLines.mutateAsync({ section_id: sectionId, line_ids: lineIds });

    pushAction({
      description: 'Reorder lines',
      undo: async () => {
        await reorderLines.mutateAsync({ section_id: sectionId, line_ids: previousOrder });
      },
      redo: async () => {
        await reorderLines.mutateAsync({ section_id: sectionId, line_ids: lineIds });
      },
    });
  }, [song, reorderLines, pushAction]);

  const handleDelete = async () => {
    await deleteSong.mutateAsync(resolvedParams.id);
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
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </Link>
            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
              Songwriter
            </span>
          </div>
          <div className="flex items-center gap-2">
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
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="px-3 py-1.5 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              Delete
            </button>
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

      {/* Main Split Pane Layout */}
      <SplitPaneLayout
        leftPanel={
          <ToolboxPanel
            song={song}
            selectedSectionId={selectedSectionId}
            onSelectSection={setSelectedSectionId}
            onUpdateSong={handleUpdateSong}
            onUpdateLine={handleUpdateLine}
            onAddLine={handleAddLine}
            onAddLineWithText={handleAddLineWithText}
            onDeleteLine={handleDeleteLine}
            onDeleteSection={handleDeleteSection}
            onUpdateSection={handleUpdateSection}
            onReorderSections={handleReorderSections}
            onReorderLines={handleReorderLines}
            onAddSection={handleAddSection}
            isUpdating={updateSong.isPending}
            isMutating={
              addLine.isPending ||
              deleteLine.isPending ||
              updateLine.isPending ||
              updateSectionMutation.isPending ||
              reorderSections.isPending ||
              deleteSectionMutation.isPending ||
              reorderLines.isPending
            }
          />
        }
        rightPanel={
          <LivePreviewPanel
            song={song}
            selectedSectionId={selectedSectionId}
            onSectionClick={setSelectedSectionId}
          />
        }
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
                disabled={deleteSong.isPending}
                className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                {deleteSong.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
