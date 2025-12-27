/**
 * React Query hooks for admin.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createInvite,
  deleteUser,
  getCosts,
  GetCostsParams,
  getUser,
  listInvites,
  ListInvitesParams,
  listUsers,
  ListUsersParams,
  revokeInvite,
  updateUser,
} from '@/lib/admin';
import { InviteCreateRequest, UserUpdateRequest } from '@/types/admin';

// Query keys
export const adminKeys = {
  all: ['admin'] as const,
  users: () => [...adminKeys.all, 'users'] as const,
  usersList: (params: ListUsersParams) => [...adminKeys.users(), 'list', params] as const,
  user: (userId: string) => [...adminKeys.users(), userId] as const,
  invites: () => [...adminKeys.all, 'invites'] as const,
  invitesList: (params: ListInvitesParams) => [...adminKeys.invites(), 'list', params] as const,
  costs: () => [...adminKeys.all, 'costs'] as const,
  costsSummary: (params: GetCostsParams) => [...adminKeys.costs(), 'summary', params] as const,
};

// User hooks

/**
 * List all users.
 */
export function useUsers(params: ListUsersParams = {}) {
  return useQuery({
    queryKey: adminKeys.usersList(params),
    queryFn: () => listUsers(params),
  });
}

/**
 * Get a specific user.
 */
export function useUser(userId: string) {
  return useQuery({
    queryKey: adminKeys.user(userId),
    queryFn: () => getUser(userId),
    enabled: !!userId,
  });
}

/**
 * Update a user.
 */
export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, request }: { userId: string; request: UserUpdateRequest }) =>
      updateUser(userId, request),
    onSuccess: (user) => {
      queryClient.setQueryData(adminKeys.user(user.id), user);
      queryClient.invalidateQueries({ queryKey: adminKeys.users() });
    },
  });
}

/**
 * Delete a user.
 */
export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: (_, userId) => {
      queryClient.removeQueries({ queryKey: adminKeys.user(userId) });
      queryClient.invalidateQueries({ queryKey: adminKeys.users() });
    },
  });
}

// Invite hooks

/**
 * List all invites.
 */
export function useInvites(params: ListInvitesParams = {}) {
  return useQuery({
    queryKey: adminKeys.invitesList(params),
    queryFn: () => listInvites(params),
  });
}

/**
 * Create an invite.
 */
export function useCreateInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: InviteCreateRequest) => createInvite(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.invites() });
    },
  });
}

/**
 * Revoke an invite.
 */
export function useRevokeInvite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => revokeInvite(code),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: adminKeys.invites() });
    },
  });
}

// Cost hooks

/**
 * Get cost summary.
 */
export function useCosts(params: GetCostsParams = {}) {
  return useQuery({
    queryKey: adminKeys.costsSummary(params),
    queryFn: () => getCosts(params),
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  });
}
