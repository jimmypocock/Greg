'use client';

import { useState } from 'react';
import { useUsers, useUpdateUser, useDeleteUser } from '@/hooks/queries/admin';
import { AdminUser } from '@/types/admin';

export default function UsersPage() {
  const [filters, setFilters] = useState({
    is_active: undefined as boolean | undefined,
    role: undefined as string | undefined,
  });

  const { data, isLoading, error } = useUsers({
    limit: 50,
    is_active: filters.is_active,
    role: filters.role,
  });

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Users</h1>
        <p className="mt-1 text-sm text-gray-600">
          Manage user accounts and permissions
        </p>
      </div>

      {/* Filters */}
      <div className="mb-6 flex gap-4">
        <select
          value={filters.is_active === undefined ? '' : filters.is_active.toString()}
          onChange={(e) => setFilters({
            ...filters,
            is_active: e.target.value === '' ? undefined : e.target.value === 'true',
          })}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>

        <select
          value={filters.role || ''}
          onChange={(e) => setFilters({
            ...filters,
            role: e.target.value || undefined,
          })}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
        >
          <option value="">All Roles</option>
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="mt-2 text-sm text-gray-500">Loading users...</p>
          </div>
        ) : error ? (
          <div className="p-8 text-center text-red-600">
            Error loading users
          </div>
        ) : data?.users.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No users found
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Role
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {data?.users.map((user) => (
                <UserRow key={user.id} user={user} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {data && (
        <p className="mt-4 text-sm text-gray-500">
          Showing {data.users.length} of {data.total} users
        </p>
      )}
    </div>
  );
}

function UserRow({ user }: { user: AdminUser }) {
  const [isEditing, setIsEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const updateUser = useUpdateUser();
  const deleteUser = useDeleteUser();

  const handleToggleActive = () => {
    updateUser.mutate({
      userId: user.id,
      request: { is_active: !user.is_active },
    });
  };

  const handleRoleChange = (newRole: string) => {
    updateUser.mutate({
      userId: user.id,
      request: { role: newRole },
    });
    setIsEditing(false);
  };

  const handleDelete = () => {
    deleteUser.mutate(user.id);
    setShowDeleteConfirm(false);
  };

  return (
    <tr>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center mr-3">
            <span className="text-xs font-medium text-indigo-600">
              {user.email[0].toUpperCase()}
            </span>
          </div>
          <div>
            <div className="text-sm font-medium text-gray-900">{user.email}</div>
            {user.is_verified && (
              <span className="text-xs text-green-600">Verified</span>
            )}
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        {isEditing ? (
          <select
            value={user.role}
            onChange={(e) => handleRoleChange(e.target.value)}
            className="text-sm border border-gray-200 rounded px-2 py-1"
            autoFocus
            onBlur={() => setIsEditing(false)}
          >
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        ) : (
          <button
            onClick={() => setIsEditing(true)}
            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              user.role === 'admin'
                ? 'bg-purple-100 text-purple-800'
                : 'bg-gray-100 text-gray-800'
            } hover:opacity-80`}
          >
            {user.role}
          </button>
        )}
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <button
          onClick={handleToggleActive}
          disabled={updateUser.isPending}
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            user.is_active
              ? 'bg-green-100 text-green-800'
              : 'bg-red-100 text-red-800'
          } hover:opacity-80`}
        >
          {user.is_active ? 'Active' : 'Inactive'}
        </button>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
        {new Date(user.created_at).toLocaleDateString()}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
        {showDeleteConfirm ? (
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={handleDelete}
              disabled={deleteUser.isPending}
              className="text-red-600 hover:text-red-800"
            >
              {deleteUser.isPending ? 'Deleting...' : 'Confirm'}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="text-gray-600 hover:text-gray-800"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="text-red-600 hover:text-red-800"
          >
            Delete
          </button>
        )}
      </td>
    </tr>
  );
}
