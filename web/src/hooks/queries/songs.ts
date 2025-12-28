/**
 * React Query hooks for songs.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  listSongs,
  getSong,
  createSong,
  createSongFromMarkdown,
  quickStartSong,
  updateSong,
  deleteSong,
  suggestStructure,
  applyStructure,
  addChord,
  removeChord,
  addLine,
  updateLine,
  addSection,
  updateSection,
  reorderSections,
  deleteLine,
  deleteSection,
  reorderLines,
} from '@/lib/songs';
import {
  SongCreateRequest,
  SongUpdateRequest,
  AddChordRequest,
  RemoveChordRequest,
  AddLineRequest,
  UpdateLineRequest,
  AddSectionRequest,
  UpdateSectionRequest,
  ReorderSectionsRequest,
  DeleteLineRequest,
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
    onSuccess: () => {
      // Force refetch to ensure UI updates properly
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
    },
  });
}

// Remove chord
export function useRemoveChord(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RemoveChordRequest) => removeChord(id, data),
    onSuccess: () => {
      // Force refetch to ensure UI updates properly
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
    },
  });
}

// Add line
export function useAddLine(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: AddLineRequest) => addLine(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
    },
  });
}

// Update line
export function useUpdateLine(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: UpdateLineRequest) => updateLine(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
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

// Update section
export function useUpdateSection(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { sectionId: string } & UpdateSectionRequest) =>
      updateSection(id, data.sectionId, { type: data.type, number: data.number }),
    onSuccess: (song) => {
      queryClient.setQueryData(songKeys.detail(id), song);
      queryClient.invalidateQueries({ queryKey: songKeys.lists() });
    },
  });
}

// Reorder sections
export function useReorderSections(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ReorderSectionsRequest) => reorderSections(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
    },
  });
}

// Delete line
export function useDeleteLine(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: DeleteLineRequest) => deleteLine(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
    },
  });
}

// Delete section
export function useDeleteSection(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sectionId: string) => deleteSection(id, sectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: songKeys.lists() });
    },
  });
}

// Reorder lines within a section
export function useReorderLines(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { section_id: string; line_ids: string[] }) => reorderLines(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: songKeys.detail(id) });
    },
  });
}
