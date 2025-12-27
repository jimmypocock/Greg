'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listNotes, createNote, updateNote, deleteNote, resolveNote, unresolveNote } from '@/lib/songs';
import { SongNote, NoteType, SongNoteCreateRequest } from '@/types';

interface SongNotesPanelProps {
  songId: string;
}

const NOTE_TYPE_LABELS: Record<NoteType, { label: string; color: string; bgColor: string }> = {
  [NoteType.IDEA]: { label: 'Idea', color: 'text-purple-700', bgColor: 'bg-purple-50 border-purple-200' },
  [NoteType.INSPIRATION]: { label: 'Inspiration', color: 'text-pink-700', bgColor: 'bg-pink-50 border-pink-200' },
  [NoteType.REFERENCE]: { label: 'Reference', color: 'text-blue-700', bgColor: 'bg-blue-50 border-blue-200' },
  [NoteType.CONTEXT]: { label: 'Context', color: 'text-gray-700', bgColor: 'bg-gray-50 border-gray-200' },
  [NoteType.TODO]: { label: 'Todo', color: 'text-orange-700', bgColor: 'bg-orange-50 border-orange-200' },
  [NoteType.FEEDBACK]: { label: 'Feedback', color: 'text-green-700', bgColor: 'bg-green-50 border-green-200' },
  [NoteType.OTHER]: { label: 'Other', color: 'text-slate-700', bgColor: 'bg-slate-50 border-slate-200' },
};

export function SongNotesPanel({ songId }: SongNotesPanelProps) {
  const queryClient = useQueryClient();
  const [isAddingNote, setIsAddingNote] = useState(false);
  const [newNoteType, setNewNoteType] = useState<NoteType>(NoteType.IDEA);
  const [newNoteTitle, setNewNoteTitle] = useState('');
  const [newNoteContent, setNewNoteContent] = useState('');
  const [filterType, setFilterType] = useState<NoteType | 'all'>('all');
  const [showResolved, setShowResolved] = useState(true);
  const [editingNote, setEditingNote] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');

  const { data: notesData, isLoading } = useQuery({
    queryKey: ['notes', songId, filterType, showResolved],
    queryFn: () => listNotes(songId, {
      noteType: filterType === 'all' ? undefined : filterType,
      includeResolved: showResolved,
    }),
  });

  const createNoteMutation = useMutation({
    mutationFn: (data: SongNoteCreateRequest) => createNote(songId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', songId] });
      setIsAddingNote(false);
      setNewNoteTitle('');
      setNewNoteContent('');
      setNewNoteType(NoteType.IDEA);
    },
  });

  const updateNoteMutation = useMutation({
    mutationFn: ({ noteId, content }: { noteId: string; content: string }) =>
      updateNote(songId, noteId, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', songId] });
      setEditingNote(null);
      setEditContent('');
    },
  });

  const deleteNoteMutation = useMutation({
    mutationFn: (noteId: string) => deleteNote(songId, noteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', songId] });
    },
  });

  const resolveNoteMutation = useMutation({
    mutationFn: (noteId: string) => resolveNote(songId, noteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', songId] });
    },
  });

  const unresolveNoteMutation = useMutation({
    mutationFn: (noteId: string) => unresolveNote(songId, noteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', songId] });
    },
  });

  const handleAddNote = () => {
    if (!newNoteContent.trim()) return;
    createNoteMutation.mutate({
      note_type: newNoteType,
      title: newNoteTitle.trim() || undefined,
      content: newNoteContent.trim(),
    });
  };

  const handleStartEdit = (note: SongNote) => {
    setEditingNote(note.id);
    setEditContent(note.content);
  };

  const handleSaveEdit = (noteId: string) => {
    if (!editContent.trim()) return;
    updateNoteMutation.mutate({ noteId, content: editContent.trim() });
  };

  const notes = notesData?.notes || [];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Brain Dump</h3>
        <button
          onClick={() => setIsAddingNote(true)}
          className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          + Add Note
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value as NoteType | 'all')}
          className="text-sm border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
        >
          <option value="all">All Types</option>
          {Object.entries(NOTE_TYPE_LABELS).map(([type, { label }]) => (
            <option key={type} value={type}>{label}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          Show resolved
        </label>
      </div>

      {/* Add Note Form */}
      {isAddingNote && (
        <div className="mb-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="flex gap-2 mb-3">
            <select
              value={newNoteType}
              onChange={(e) => setNewNoteType(e.target.value as NoteType)}
              className="text-sm border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            >
              {Object.entries(NOTE_TYPE_LABELS).map(([type, { label }]) => (
                <option key={type} value={type}>{label}</option>
              ))}
            </select>
            <input
              type="text"
              value={newNoteTitle}
              onChange={(e) => setNewNoteTitle(e.target.value)}
              placeholder="Title (optional)"
              className="flex-1 text-sm border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            />
          </div>
          <textarea
            value={newNoteContent}
            onChange={(e) => setNewNoteContent(e.target.value)}
            placeholder="What's on your mind about this song?"
            rows={3}
            className="w-full text-sm border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          />
          <div className="mt-3 flex justify-end gap-2">
            <button
              onClick={() => setIsAddingNote(false)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
            <button
              onClick={handleAddNote}
              disabled={!newNoteContent.trim() || createNoteMutation.isPending}
              className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
            >
              {createNoteMutation.isPending ? 'Adding...' : 'Add Note'}
            </button>
          </div>
        </div>
      )}

      {/* Notes List */}
      {isLoading ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-indigo-600 mx-auto"></div>
        </div>
      ) : notes.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No notes yet. Add ideas, inspirations, or context for your song.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {notes.map((note) => {
            const typeInfo = NOTE_TYPE_LABELS[note.note_type];
            const isEditing = editingNote === note.id;

            return (
              <div
                key={note.id}
                className={`p-3 rounded-lg border ${typeInfo.bgColor} ${
                  note.is_resolved ? 'opacity-60' : ''
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${typeInfo.color}`}>
                      {typeInfo.label}
                    </span>
                    {note.title && (
                      <span className="text-sm font-medium text-gray-900">
                        {note.title}
                      </span>
                    )}
                    {note.is_resolved && (
                      <span className="text-xs text-gray-500">(resolved)</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1">
                    {note.note_type === NoteType.TODO && (
                      <button
                        onClick={() =>
                          note.is_resolved
                            ? unresolveNoteMutation.mutate(note.id)
                            : resolveNoteMutation.mutate(note.id)
                        }
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        {note.is_resolved ? 'Reopen' : 'Done'}
                      </button>
                    )}
                    {!isEditing && (
                      <button
                        onClick={() => handleStartEdit(note)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        Edit
                      </button>
                    )}
                    <button
                      onClick={() => deleteNoteMutation.mutate(note.id)}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Delete
                    </button>
                  </div>
                </div>
                {isEditing ? (
                  <div>
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      rows={3}
                      className="w-full text-sm border-gray-300 rounded-md shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
                    />
                    <div className="mt-2 flex justify-end gap-2">
                      <button
                        onClick={() => setEditingNote(null)}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => handleSaveEdit(note.id)}
                        disabled={updateNoteMutation.isPending}
                        className="text-xs text-indigo-600 hover:text-indigo-800"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-700 whitespace-pre-wrap">
                    {note.content}
                  </p>
                )}
                <div className="mt-2 text-xs text-gray-400">
                  {new Date(note.created_at).toLocaleDateString()}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
