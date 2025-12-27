/**
 * Collaboration types for the Songwriter app.
 */

export type CollaboratorRole = 'owner' | 'editor' | 'viewer';

export interface Collaborator {
  id: string;
  song_id: string;
  user_id: string;
  role: CollaboratorRole;
  invited_by: string | null;
  invited_at: string;
  accepted_at: string | null;
  is_pending: boolean;
}

export interface CollaboratorListResponse {
  collaborators: Collaborator[];
  total: number;
}

export interface AddCollaboratorRequest {
  user_id: string;
  role: CollaboratorRole;
}

export interface UpdateCollaboratorRequest {
  role: CollaboratorRole;
}

export interface ShareLink {
  id: string;
  song_id: string;
  token: string;
  role: CollaboratorRole;
  created_by: string;
  created_at: string;
  expires_at: string | null;
  max_uses: number | null;
  use_count: number;
  is_active: boolean;
  is_valid: boolean;
  share_url: string;
}

export interface ShareLinkListResponse {
  share_links: ShareLink[];
  total: number;
}

export interface CreateShareLinkRequest {
  role: CollaboratorRole;
  expires_at?: string | null;
  max_uses?: number | null;
}

export interface ShareLinkInfo {
  song_id: string;
  song_title: string;
  role: CollaboratorRole;
  is_valid: boolean;
  message: string;
}

export interface AcceptShareLinkResponse {
  song_id: string;
  song_title: string;
  role: CollaboratorRole;
  message: string;
}
