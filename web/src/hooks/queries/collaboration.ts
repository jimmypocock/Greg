/**
 * React Query hooks for collaboration.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  acceptShareLink,
  addCollaborator,
  createShareLink,
  deleteShareLink,
  getShareLinkInfo,
  listCollaborators,
  listShareLinks,
  removeCollaborator,
  updateCollaborator,
} from '@/lib/collaboration';
import {
  AddCollaboratorRequest,
  CreateShareLinkRequest,
  UpdateCollaboratorRequest,
} from '@/types/collaboration';

// Query keys
export const collaborationKeys = {
  all: ['collaboration'] as const,
  collaborators: (songId: string) => [...collaborationKeys.all, 'collaborators', songId] as const,
  shareLinks: (songId: string) => [...collaborationKeys.all, 'shareLinks', songId] as const,
  shareLinkInfo: (token: string) => [...collaborationKeys.all, 'shareLinkInfo', token] as const,
};

// Collaborator hooks

/**
 * List collaborators for a song.
 */
export function useCollaborators(songId: string) {
  return useQuery({
    queryKey: collaborationKeys.collaborators(songId),
    queryFn: () => listCollaborators(songId),
    enabled: !!songId,
  });
}

/**
 * Add a collaborator to a song.
 */
export function useAddCollaborator(songId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: AddCollaboratorRequest) => addCollaborator(songId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.collaborators(songId) });
    },
  });
}

/**
 * Update a collaborator's role.
 */
export function useUpdateCollaborator(songId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      collaboratorId,
      request,
    }: {
      collaboratorId: string;
      request: UpdateCollaboratorRequest;
    }) => updateCollaborator(songId, collaboratorId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.collaborators(songId) });
    },
  });
}

/**
 * Remove a collaborator from a song.
 */
export function useRemoveCollaborator(songId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (collaboratorId: string) => removeCollaborator(songId, collaboratorId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.collaborators(songId) });
    },
  });
}

// Share link hooks

/**
 * List share links for a song.
 */
export function useShareLinks(songId: string, includeInactive = false) {
  return useQuery({
    queryKey: collaborationKeys.shareLinks(songId),
    queryFn: () => listShareLinks(songId, includeInactive),
    enabled: !!songId,
  });
}

/**
 * Create a share link for a song.
 */
export function useCreateShareLink(songId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: CreateShareLinkRequest) => createShareLink(songId, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.shareLinks(songId) });
    },
  });
}

/**
 * Delete a share link.
 */
export function useDeleteShareLink(songId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (linkId: string) => deleteShareLink(songId, linkId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: collaborationKeys.shareLinks(songId) });
    },
  });
}

// Public share link hooks

/**
 * Get share link info.
 */
export function useShareLinkInfo(token: string) {
  return useQuery({
    queryKey: collaborationKeys.shareLinkInfo(token),
    queryFn: () => getShareLinkInfo(token),
    enabled: !!token,
  });
}

/**
 * Accept a share link.
 */
export function useAcceptShareLink() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => acceptShareLink(token),
    onSuccess: () => {
      // Invalidate songs list as user now has access to a new song
      queryClient.invalidateQueries({ queryKey: ['songs'] });
    },
  });
}
