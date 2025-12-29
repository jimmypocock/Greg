/**
 * Songs API functions.
 */

import { get, post, put, del } from './api';
import {
  Song,
  SongListResponse,
  SongCreateRequest,
  SongUpdateRequest,
  MarkdownInput,
  AddChordRequest,
  RemoveChordRequest,
  AddLineRequest,
  UpdateLineRequest,
  AddSectionRequest,
  UpdateSectionRequest,
  ReorderSectionsRequest,
  DeleteLineRequest,
  ApplyStructureRequest,
  StructureSuggestion,
  SongNote,
  SongNotesListResponse,
  SongNoteCreateRequest,
  SongNoteUpdateRequest,
  ContextResponse,
  NoteType,
  QuickStartRequest,
  QuickStartResponse,
} from '@/types';

// List all songs
export async function listSongs(): Promise<SongListResponse> {
  return get<SongListResponse>('/songs/');
}

// Get a single song
export async function getSong(id: string): Promise<Song> {
  return get<Song>(`/songs/${id}`);
}

// Create a new song
export async function createSong(data: SongCreateRequest): Promise<Song> {
  return post<Song, SongCreateRequest>('/songs/', data);
}

// Create a song from markdown
export async function createSongFromMarkdown(content: string): Promise<Song> {
  return post<Song, MarkdownInput>('/songs/from-markdown', { content });
}

// Quick-start a new song for exploration
export async function quickStartSong(data: QuickStartRequest = {}): Promise<QuickStartResponse> {
  return post<QuickStartResponse, QuickStartRequest>('/songs/quick-start', data);
}

// Update a song
export async function updateSong(id: string, data: SongUpdateRequest): Promise<Song> {
  return put<Song, SongUpdateRequest>(`/songs/${id}`, data);
}

// Delete a song
export async function deleteSong(id: string): Promise<void> {
  return del(`/songs/${id}`);
}

// Get AI structure suggestion
export async function suggestStructure(id: string): Promise<StructureSuggestion> {
  return post<StructureSuggestion, object>(`/songs/${id}/suggest-structure`, {});
}

// Apply a structure to a song
export async function applyStructure(id: string, data: ApplyStructureRequest): Promise<Song> {
  return post<Song, ApplyStructureRequest>(`/songs/${id}/apply-structure`, data);
}

// Add a chord to a line
export async function addChord(id: string, data: AddChordRequest): Promise<Song> {
  return post<Song, AddChordRequest>(`/songs/${id}/chords`, data);
}

// Remove a chord from a line
export async function removeChord(id: string, data: RemoveChordRequest): Promise<Song> {
  return del<Song>(`/songs/${id}/chords`, data);
}

// Add a new line to a section
export async function addLine(id: string, data: AddLineRequest): Promise<Song> {
  return post<Song, AddLineRequest>(`/songs/${id}/lines`, data);
}

// Update a line's text
export async function updateLine(id: string, data: UpdateLineRequest): Promise<Song> {
  return put<Song, UpdateLineRequest>(`/songs/${id}/lines`, data);
}

// Add a new section
export async function addSection(id: string, data: AddSectionRequest): Promise<Song> {
  return post<Song, AddSectionRequest>(`/songs/${id}/sections`, data);
}

// Update a section
export async function updateSection(id: string, sectionId: string, data: UpdateSectionRequest): Promise<Song> {
  return put<Song, UpdateSectionRequest>(`/songs/${id}/sections/${sectionId}`, data);
}

// Reorder sections
export async function reorderSections(id: string, data: ReorderSectionsRequest): Promise<Song> {
  return put<Song, ReorderSectionsRequest>(`/songs/${id}/sections/reorder`, data);
}

// Delete a line
export async function deleteLine(id: string, data: DeleteLineRequest): Promise<Song> {
  return del<Song>(`/songs/${id}/lines`, data);
}

// Delete a section
export async function deleteSection(id: string, sectionId: string): Promise<Song> {
  return del<Song>(`/songs/${id}/sections/${sectionId}`);
}

// Reorder lines within a section
export async function reorderLines(id: string, data: { section_id: string; line_ids: string[] }): Promise<Song> {
  return put<Song, { section_id: string; line_ids: string[] }>(`/songs/${id}/lines/reorder`, data);
}

// Get chord sheet (text format)
export async function getChordSheet(id: string): Promise<string> {
  return get<string>(`/songs/${id}/chord-sheet`);
}

// ============================================================================
// Song Notes API
// ============================================================================

// List notes for a song
export async function listNotes(
  songId: string,
  options?: { noteType?: NoteType; includeResolved?: boolean }
): Promise<SongNotesListResponse> {
  const params = new URLSearchParams();
  if (options?.noteType) {
    params.append('note_type', options.noteType);
  }
  if (options?.includeResolved !== undefined) {
    params.append('include_resolved', String(options.includeResolved));
  }
  const query = params.toString() ? `?${params.toString()}` : '';
  return get<SongNotesListResponse>(`/songs/${songId}/notes${query}`);
}

// Create a new note
export async function createNote(
  songId: string,
  data: SongNoteCreateRequest
): Promise<SongNote> {
  return post<SongNote, SongNoteCreateRequest>(`/songs/${songId}/notes`, data);
}

// Get a specific note
export async function getNote(songId: string, noteId: string): Promise<SongNote> {
  return get<SongNote>(`/songs/${songId}/notes/${noteId}`);
}

// Update a note
export async function updateNote(
  songId: string,
  noteId: string,
  data: SongNoteUpdateRequest
): Promise<SongNote> {
  return put<SongNote, SongNoteUpdateRequest>(`/songs/${songId}/notes/${noteId}`, data);
}

// Delete a note
export async function deleteNote(songId: string, noteId: string): Promise<void> {
  return del(`/songs/${songId}/notes/${noteId}`);
}

// Resolve a note (mark as done)
export async function resolveNote(songId: string, noteId: string): Promise<SongNote> {
  return post<SongNote, object>(`/songs/${songId}/notes/${noteId}/resolve`, {});
}

// Unresolve a note
export async function unresolveNote(songId: string, noteId: string): Promise<SongNote> {
  return post<SongNote, object>(`/songs/${songId}/notes/${noteId}/unresolve`, {});
}

// Get AI context (all notes formatted for AI)
export async function getAIContext(songId: string): Promise<ContextResponse> {
  return get<ContextResponse>(`/songs/${songId}/context`);
}

// ============================================================================
// Canvas Editor API
// ============================================================================

import { CanvasSaveRequest } from '@/types';

// Save canvas editor content
export async function saveCanvas(id: string, data: CanvasSaveRequest): Promise<Song> {
  return put<Song, CanvasSaveRequest>(`/songs/${id}/canvas`, data);
}
