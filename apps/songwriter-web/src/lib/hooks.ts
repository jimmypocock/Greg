/**
 * React Query hooks for songs.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  listSongs,
  getSong,
  createSong,
  createSongFromMarkdown,
  updateSong,
  deleteSong,
  suggestStructure,
  applyStructure,
  addChord,
  addLine,
  updateLine,
  addSection,
} from './songs';
import {
  SongCreateRequest,
  SongUpdateRequest,
  AddChordRequest,
  AddLineRequest,
  UpdateLineRequest,
  AddSectionRequest,
  ApplyStructureRequest,
} from '@/types';

// Query keys
export const songKeys = {
  all: ['songs'] as const,
  lists: () => [...songKeys.all, 'list'] as const,
  list: () => [...songKeys.lists()] as const,
  details: () => [...songKeys.all, 'detail'] as const,
  detail: (id: string) => [...songKeys.details(), id] as const,
};

// List songs
export function useSongs() {
  return useQuery({
    queryKey: songKeys.list(),
    queryFn: listSongs,
  });
}

// Get single song
export function useSong(id: string) {
  return useQuery({
    queryKey: songKeys.detail(id),
    queryFn: () => getSong(id),
    enabled: !!id,
  });
}

// Create song
export function useCreateSong() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SongCreateRequest) => createSong(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.lists() });
    },
  });
}

// Create song from markdown
export function useCreateSongFromMarkdown() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => createSongFromMarkdown(content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.lists() });
    },
  });
}

// Update song
export function useUpdateSong(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SongUpdateRequest) => updateSong(id, data),
    onSuccess: (song) => {
      queryClient.setQueryData(songKeys.detail(id), song);
      queryClient.invalidateQueries({ queryKey: songKeys.lists() });
    },
  });
}

// Delete song
export function useDeleteSong() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteSong(id),
    onSuccess: (_, id) => {
      queryClient.removeQueries({ queryKey: songKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: songKeys.lists() });
    },
  });
}

// Suggest structure
export function useSuggestStructure(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => suggestStructure(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
    },
  });
}

// Apply structure
export function useApplyStructure(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ApplyStructureRequest) => applyStructure(id, data),
    onSuccess: (song) => {
      queryClient.setQueryData(songKeys.detail(id), song);
      queryClient.invalidateQueries({ queryKey: songKeys.lists() });
    },
  });
}

// Add chord
export function useAddChord(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AddChordRequest) => addChord(id, data),
    onSuccess: (song) => {
      queryClient.setQueryData(songKeys.detail(id), song);
    },
  });
}

// Add line
export function useAddLine(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AddLineRequest) => addLine(id, data),
    onSuccess: (song) => {
      queryClient.setQueryData(songKeys.detail(id), song);
    },
  });
}

// Update line
export function useUpdateLine(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UpdateLineRequest) => updateLine(id, data),
    onSuccess: (song) => {
      queryClient.setQueryData(songKeys.detail(id), song);
    },
  });
}

// Add section
export function useAddSection(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AddSectionRequest) => addSection(id, data),
    onSuccess: (song) => {
      queryClient.setQueryData(songKeys.detail(id), song);
      queryClient.invalidateQueries({ queryKey: songKeys.lists() });
    },
  });
}
