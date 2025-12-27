/**
 * Admin API functions for the Songwriter app.
 */

import { del, get, patch, post } from './api';
import {
  AdminUser,
  CostSummary,
  InviteCreateRequest,
  InviteDetail,
  InviteListResponse,
  InviteResponse,
  MessageResponse,
  UserListResponse,
  UserResponse,
  UserUpdateRequest,
} from '@/types/admin';

// User management endpoints

export interface ListUsersParams {
  skip?: number;
  limit?: number;
  is_active?: boolean;
  role?: string;
}

/**
 * List all users (admin only).
 */
export async function listUsers(params: ListUsersParams = {}): Promise<UserListResponse> {
  const searchParams = new URLSearchParams();
  if (params.skip !== undefined) searchParams.set('skip', params.skip.toString());
  if (params.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params.is_active !== undefined) searchParams.set('is_active', params.is_active.toString());
  if (params.role) searchParams.set('role', params.role);

  const query = searchParams.toString();
  return get<UserListResponse>(`/admin/users${query ? `?${query}` : ''}`);
}

/**
 * Get a specific user (admin only).
 */
export async function getUser(userId: string): Promise<AdminUser> {
  const response = await get<UserResponse>(`/admin/users/${userId}`);
  return response.user;
}

/**
 * Update a user (admin only).
 */
export async function updateUser(userId: string, request: UserUpdateRequest): Promise<AdminUser> {
  const response = await patch<UserResponse, UserUpdateRequest>(`/admin/users/${userId}`, request);
  return response.user;
}

/**
 * Delete a user (admin only).
 */
export async function deleteUser(userId: string): Promise<MessageResponse> {
  return del<MessageResponse>(`/admin/users/${userId}`);
}

// Invite management endpoints

export interface ListInvitesParams {
  skip?: number;
  limit?: number;
  active?: boolean;
  used?: boolean;
}

/**
 * List all invites (admin only).
 */
export async function listInvites(params: ListInvitesParams = {}): Promise<InviteListResponse> {
  const searchParams = new URLSearchParams();
  if (params.skip !== undefined) searchParams.set('skip', params.skip.toString());
  if (params.limit !== undefined) searchParams.set('limit', params.limit.toString());
  if (params.active !== undefined) searchParams.set('active', params.active.toString());
  if (params.used !== undefined) searchParams.set('used', params.used.toString());

  const query = searchParams.toString();
  return get<InviteListResponse>(`/admin/invites${query ? `?${query}` : ''}`);
}

/**
 * Create an invite (admin only).
 */
export async function createInvite(request: InviteCreateRequest): Promise<InviteDetail> {
  const response = await post<InviteResponse, InviteCreateRequest>('/admin/invites', request);
  return response.invite;
}

/**
 * Revoke an invite (admin only).
 */
export async function revokeInvite(code: string): Promise<MessageResponse> {
  return del<MessageResponse>(`/admin/invites/${code}`);
}

// Cost management endpoints

export interface GetCostsParams {
  days?: number;
  user_id?: string;
}

/**
 * Get cost summary (admin only).
 */
export async function getCosts(params: GetCostsParams = {}): Promise<CostSummary> {
  const searchParams = new URLSearchParams();
  if (params.days !== undefined) searchParams.set('days', params.days.toString());
  if (params.user_id) searchParams.set('user_id', params.user_id);

  const query = searchParams.toString();
  return get<CostSummary>(`/admin/costs${query ? `?${query}` : ''}`);
}
