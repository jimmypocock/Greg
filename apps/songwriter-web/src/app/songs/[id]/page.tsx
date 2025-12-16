'use client';

import { use, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useSong, useUpdateSong, useDeleteSong, useSuggestStructure, useApplyStructure, useUpdateLine, useAddLine } from '@/lib/hooks';
import { StatusBadge } from '@/components/StatusBadge';
import { SectionEditor } from '@/components/SectionEditor';
import { AgentReviewPanel } from '@/components/AgentReviewPanel';
import { ReviewHistory } from '@/components/ReviewHistory';
import { SongNotesPanel } from '@/components/SongNotesPanel';
import { SongStatus, StructureSuggestion } from '@/types';

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

  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editKey, setEditKey] = useState('');
  const [editTempo, setEditTempo] = useState('');
  const [suggestion, setSuggestion] = useState<StructureSuggestion | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleEdit = () => {
    if (song) {
      setEditTitle(song.title);
      setEditKey(song.key || '');
      setEditTempo(song.tempo?.toString() || '');
      setIsEditing(true);
    }
  };

  const handleSave = async () => {
    await updateSong.mutateAsync({
      title: editTitle || undefined,
      key: editKey || undefined,
      tempo: editTempo ? parseInt(editTempo, 10) : undefined,
    });
    setIsEditing(false);
  };

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

  const handleStatusChange = async (status: SongStatus) => {
    await updateSong.mutateAsync({ status });
  };

  const handleUpdateLine = async (sectionId: string, lineId: string, text: string) => {
    await updateLine.mutateAsync({ section_id: sectionId, line_id: lineId, text });
  };

  const handleAddLine = async (sectionId: string) => {
    await addLine.mutateAsync({ section_id: sectionId, text: '' });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-500">Loading song...</p>
        </div>
      </div>
    );
  }

  if (error || !song) {
    return (
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-5xl mx-auto px-4 py-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-red-800">Error loading song</h3>
            <p className="mt-1 text-sm text-red-700">
              {error instanceof Error ? error.message : 'Song not found'}
            </p>
            <Link href="/" className="mt-4 inline-block text-sm text-indigo-600 hover:text-indigo-500">
              &larr; Back to songs
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <Link href="/" className="text-gray-500 hover:text-gray-700">
                &larr;
              </Link>
              {isEditing ? (
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  className="text-2xl font-bold text-gray-900 border-b-2 border-indigo-500 focus:outline-none"
                />
              ) : (
                <h1 className="text-2xl font-bold text-gray-900">{song.title}</h1>
              )}
              <StatusBadge status={song.status} />
            </div>
            <div className="flex items-center gap-2">
              {isEditing ? (
                <>
                  <button
                    onClick={() => setIsEditing(false)}
                    className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={updateSong.isPending}
                    className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
                  >
                    Save
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={handleEdit}
                    className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => setShowDeleteConfirm(true)}
                    className="px-3 py-1.5 text-sm text-red-600 hover:text-red-800"
                  >
                    Delete
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-500">
            {isEditing ? (
              <>
                <div className="flex items-center gap-2">
                  <label htmlFor="key">Key:</label>
                  <input
                    id="key"
                    type="text"
                    value={editKey}
                    onChange={(e) => setEditKey(e.target.value)}
                    placeholder="e.g., G major"
                    className="w-24 px-2 py-1 border rounded text-sm"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label htmlFor="tempo">BPM:</label>
                  <input
                    id="tempo"
                    type="number"
                    value={editTempo}
                    onChange={(e) => setEditTempo(e.target.value)}
                    placeholder="120"
                    className="w-20 px-2 py-1 border rounded text-sm"
                  />
                </div>
              </>
            ) : (
              <>
                {song.key && <span>Key: {song.key}</span>}
                {song.tempo && <span>{song.tempo} BPM</span>}
                {song.time_signature && <span>{song.time_signature}</span>}
                {song.feel && <span>Feel: {song.feel}</span>}
              </>
            )}
          </div>

          {/* Status selector */}
          <div className="mt-4">
            <select
              value={song.status}
              onChange={(e) => handleStatusChange(e.target.value as SongStatus)}
              className="text-sm border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            >
              <option value={SongStatus.IDEA}>Idea</option>
              <option value={SongStatus.DRAFT}>Draft</option>
              <option value={SongStatus.IN_PROGRESS}>In Progress</option>
              <option value={SongStatus.REVIEW}>Review</option>
              <option value={SongStatus.FINISHED}>Finished</option>
            </select>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* AI Structure Suggestion */}
        {song.raw_input && song.sections.length === 0 && (
          <div className="mb-8 bg-indigo-50 border border-indigo-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-indigo-800">Unstructured lyrics detected</h3>
            <p className="mt-1 text-sm text-indigo-700">
              This song has raw lyrics but no sections. Would you like AI to suggest a structure?
            </p>
            <button
              onClick={handleSuggestStructure}
              disabled={suggestStructure.isPending}
              className="mt-3 px-4 py-2 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              {suggestStructure.isPending ? 'Analyzing...' : 'Suggest Structure'}
            </button>
          </div>
        )}

        {/* Structure Suggestion Modal */}
        {suggestion && (
          <div className="mb-8 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-sm font-medium text-green-800">
                  Structure Suggestion ({Math.round(suggestion.confidence * 100)}% confidence)
                </h3>
                {suggestion.reasoning && (
                  <p className="mt-1 text-sm text-green-700">{suggestion.reasoning}</p>
                )}
              </div>
              <button
                onClick={() => setSuggestion(null)}
                className="text-green-600 hover:text-green-800"
              >
                &times;
              </button>
            </div>
            <div className="mt-4 space-y-2">
              {suggestion.sections.map((section, i) => (
                <div key={i} className="bg-white rounded p-2 text-sm">
                  <span className="font-medium">
                    {section.type}
                    {section.number && ` ${section.number}`}
                  </span>
                  <span className="text-gray-500 ml-2">
                    ({section.lines.length} lines)
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleApplyStructure}
                disabled={applyStructure.isPending}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {applyStructure.isPending ? 'Applying...' : 'Apply Structure'}
              </button>
              <button
                onClick={() => setSuggestion(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Sections */}
        {song.sections.length > 0 ? (
          <div className="space-y-4">
            <h2 className="text-lg font-medium text-gray-900">
              Sections ({song.sections.length})
            </h2>
            {song.sections.map((section) => (
              <SectionEditor
                key={section.id}
                section={section}
                onUpdateLine={handleUpdateLine}
                onAddLine={handleAddLine}
              />
            ))}
          </div>
        ) : song.raw_input ? (
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Raw Lyrics</h3>
            <pre className="whitespace-pre-wrap font-mono text-sm text-gray-600">
              {song.raw_input}
            </pre>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <p>This song has no content yet.</p>
          </div>
        )}

        {/* AI Review Section */}
        <div className="mt-8 space-y-4">
          <h2 className="text-lg font-medium text-gray-900">AI Critic</h2>
          <AgentReviewPanel songId={resolvedParams.id} hasSections={song.sections.length > 0} />
          <ReviewHistory songId={resolvedParams.id} />
        </div>

        {/* Brain Dump / Notes */}
        <div className="mt-8">
          <SongNotesPanel songId={resolvedParams.id} />
        </div>

        {/* Quick Notes (legacy) */}
        {song.notes && (
          <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-yellow-800">Quick Notes</h3>
            <p className="mt-1 text-sm text-yellow-700 whitespace-pre-wrap">{song.notes}</p>
          </div>
        )}
      </main>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm mx-4">
            <h3 className="text-lg font-medium text-gray-900">Delete Song</h3>
            <p className="mt-2 text-sm text-gray-500">
              Are you sure you want to delete &quot;{song.title}&quot;? This action cannot be undone.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteSong.isPending}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
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
