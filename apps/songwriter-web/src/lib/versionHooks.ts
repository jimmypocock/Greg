/**
 * React Query hooks for section version operations.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  listVersions,
  getVersion,
  createVersion,
  updateVersion,
  deleteVersion,
  duplicateVersion,
  promoteVersion,
} from './versions';
import { songKeys } from './hooks';
import type { CreateVersionRequest, UpdateVersionRequest } from '@/types/song';

// Query keys
export const versionKeys = {
  all: ['versions'] as const,
  bySection: (songId: string, sectionId: string) =>
    [...versionKeys.all, songId, sectionId] as const,
  detail: (songId: string, sectionId: string, versionId: string) =>
    [...versionKeys.all, songId, sectionId, versionId] as const,
};

/**
 * List all versions for a section.
 */
export function useSectionVersions(songId: string, sectionId: string) {
  return useQuery({
    queryKey: versionKeys.bySection(songId, sectionId),
    queryFn: () => listVersions(songId, sectionId),
    enabled: !!songId && !!sectionId,
  });
}

/**
 * Get a specific version with all its lines.
 */
export function useSectionVersion(
  songId: string,
  sectionId: string,
  versionId: string
) {
  return useQuery({
    queryKey: versionKeys.detail(songId, sectionId, versionId),
    queryFn: () => getVersion(songId, sectionId, versionId),
    enabled: !!songId && !!sectionId && !!versionId,
  });
}

/**
 * Create a new version for a section.
 */
export function useCreateVersion(songId: string, sectionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateVersionRequest) =>
      createVersion(songId, sectionId, data),
    onSuccess: () => {
      // Invalidate version list and song (to refresh section with new version)
      queryClient.invalidateQueries({
        queryKey: versionKeys.bySection(songId, sectionId),
      });
      queryClient.invalidateQueries({ queryKey: songKeys.detail(songId) });
    },
  });
}

/**
 * Update a version's metadata.
 */
export function useUpdateVersion(songId: string, sectionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      versionId,
      data,
    }: {
      versionId: string;
      data: UpdateVersionRequest;
    }) => updateVersion(songId, sectionId, versionId, data),
    onSuccess: (_, { versionId }) => {
      queryClient.invalidateQueries({
        queryKey: versionKeys.detail(songId, sectionId, versionId),
      });
      queryClient.invalidateQueries({
        queryKey: versionKeys.bySection(songId, sectionId),
      });
      queryClient.invalidateQueries({ queryKey: songKeys.detail(songId) });
    },
  });
}

/**
 * Delete a version.
 */
export function useDeleteVersion(songId: string, sectionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (versionId: string) =>
      deleteVersion(songId, sectionId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: versionKeys.bySection(songId, sectionId),
      });
      queryClient.invalidateQueries({ queryKey: songKeys.detail(songId) });
    },
  });
}

/**
 * Duplicate a version with all its lines.
 */
export function useDuplicateVersion(songId: string, sectionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ versionId, name }: { versionId: string; name?: string }) =>
      duplicateVersion(songId, sectionId, versionId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: versionKeys.bySection(songId, sectionId),
      });
      queryClient.invalidateQueries({ queryKey: songKeys.detail(songId) });
    },
  });
}

/**
 * Promote a version to be the main version.
 */
export function usePromoteVersion(songId: string, sectionId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (versionId: string) =>
      promoteVersion(songId, sectionId, versionId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: versionKeys.bySection(songId, sectionId),
      });
      queryClient.invalidateQueries({ queryKey: songKeys.detail(songId) });
    },
  });
}
