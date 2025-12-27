/**
 * Collaboration API functions for the Songwriter app.
 */

import { del, get, post, put } from './api';
import {
  AcceptShareLinkResponse,
  AddCollaboratorRequest,
  Collaborator,
  CollaboratorListResponse,
  CreateShareLinkRequest,
  ShareLink,
  ShareLinkInfo,
  ShareLinkListResponse,
  UpdateCollaboratorRequest,
} from '@/types/collaboration';

// Collaborator endpoints

/**
 * List all collaborators for a song.
 */
export async function listCollaborators(songId: string): Promise<CollaboratorListResponse> {
  return get<CollaboratorListResponse>(`/songs/${songId}/collaborators`);
}

/**
 * Add a collaborator to a song.
 */
export async function addCollaborator(
  songId: string,
  request: AddCollaboratorRequest
): Promise<Collaborator> {
  return post<Collaborator, AddCollaboratorRequest>(`/songs/${songId}/collaborators`, request);
}

/**
 * Update a collaborator's role.
 */
export async function updateCollaborator(
  songId: string,
  collaboratorId: string,
  request: UpdateCollaboratorRequest
): Promise<Collaborator> {
  return put<Collaborator, UpdateCollaboratorRequest>(
    `/songs/${songId}/collaborators/${collaboratorId}`,
    request
  );
}

/**
 * Remove a collaborator from a song.
 */
export async function removeCollaborator(songId: string, collaboratorId: string): Promise<void> {
  return del(`/songs/${songId}/collaborators/${collaboratorId}`);
}

// Share link endpoints

/**
 * List all share links for a song.
 */
export async function listShareLinks(
  songId: string,
  includeInactive = false
): Promise<ShareLinkListResponse> {
  const query = includeInactive ? '?include_inactive=true' : '';
  return get<ShareLinkListResponse>(`/songs/${songId}/share-links${query}`);
}

/**
 * Create a share link for a song.
 */
export async function createShareLink(
  songId: string,
  request: CreateShareLinkRequest
): Promise<ShareLink> {
  return post<ShareLink, CreateShareLinkRequest>(`/songs/${songId}/share-links`, request);
}

/**
 * Delete/revoke a share link.
 */
export async function deleteShareLink(songId: string, linkId: string): Promise<void> {
  return del(`/songs/${songId}/share-links/${linkId}`);
}

// Public share link endpoints

/**
 * Get information about a share link (before accepting).
 */
export async function getShareLinkInfo(token: string): Promise<ShareLinkInfo> {
  return get<ShareLinkInfo>(`/share/${token}`);
}

/**
 * Accept a share link and join as a collaborator.
 */
export async function acceptShareLink(token: string): Promise<AcceptShareLinkResponse> {
  return post<AcceptShareLinkResponse, Record<string, never>>(`/share/${token}/accept`, {});
}
