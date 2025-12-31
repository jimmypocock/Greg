/**
 * React Query hooks for songs.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  listSongs,
  getSong,
  createSongFromMarkdown,
  quickStartSong,
  deleteSong,
  suggestStructure,
  applyStructure,
} from '@/lib/songs';
import { ApplyStructureRequest } from '@/types';

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

// Quick start a new song (creates empty song for AI exploration)
export function useQuickStartSong() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data?: { title?: string; initial_input?: string }) => quickStartSong(data || {}),
    onSuccess: () => {
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
