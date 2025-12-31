/**
 * Songs API functions.
 */

import { get, post, del } from './api';
import {
  Song,
  SongListResponse,
  SongCreateRequest,
  ApplyStructureRequest,
  StructureSuggestion,
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
  return post<Song, { content: string }>('/songs/from-markdown', { content });
}

// Quick-start a new song for exploration
export async function quickStartSong(data: QuickStartRequest = {}): Promise<QuickStartResponse> {
  return post<QuickStartResponse, QuickStartRequest>('/songs/quick-start', data);
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
