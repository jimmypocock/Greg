'use client';

import { useState, useEffect, useRef } from 'react';
import {
  useCollaborators,
  useRemoveCollaborator,
  useUpdateCollaborator,
  useShareLinks,
  useCreateShareLink,
  useDeleteShareLink,
} from '@/hooks/queries/collaboration';
import { CollaboratorRole } from '@/types/collaboration';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  songId: string;
  songTitle: string;
}

type Tab = 'people' | 'links';

export function ShareModal({ isOpen, onClose, songId, songTitle }: ShareModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('people');
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        ref={modalRef}
        className="relative bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Share "{songTitle}"</h2>
            <p className="text-sm text-gray-500">Invite collaborators or create a share link</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setActiveTab('people')}
            className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'people'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            People
          </button>
          <button
            onClick={() => setActiveTab('links')}
            className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'links'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Get Link
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'people' ? (
            <PeopleTab songId={songId} />
          ) : (
            <LinksTab songId={songId} />
          )}
        </div>
      </div>
    </div>
  );
}

function PeopleTab({ songId }: { songId: string }) {
  const { data, isLoading } = useCollaborators(songId);
  const removeCollaborator = useRemoveCollaborator(songId);
  const updateCollaborator = useUpdateCollaborator(songId);

  const handleRoleChange = (collaboratorId: string, newRole: CollaboratorRole) => {
    updateCollaborator.mutate({
      collaboratorId,
      request: { role: newRole },
    });
  };

  const handleRemove = (collaboratorId: string) => {
    removeCollaborator.mutate(collaboratorId);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  const collaborators = data?.collaborators || [];

  if (collaborators.length === 0) {
    return (
      <div className="text-center py-8">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">No collaborators yet</h3>
        <p className="mt-1 text-sm text-gray-500">
          Create a share link to invite others.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {collaborators.map((collab) => (
        <div
          key={collab.id}
          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
              <span className="text-sm font-medium text-indigo-600">
                {collab.user_id.slice(0, 2).toUpperCase()}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-900">
                User {collab.user_id.slice(0, 8)}
              </p>
              <p className="text-xs text-gray-500">
                {collab.is_pending ? 'Pending' : 'Active'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {collab.role === 'owner' ? (
              <span className="px-3 py-1 text-xs font-medium bg-purple-100 text-purple-700 rounded">
                Owner
              </span>
            ) : (
              <>
                <select
                  value={collab.role}
                  onChange={(e) => handleRoleChange(collab.id, e.target.value as CollaboratorRole)}
                  className="text-sm border border-gray-200 rounded-lg px-2 py-1"
                  disabled={updateCollaborator.isPending}
                >
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                </select>
                <button
                  onClick={() => handleRemove(collab.id)}
                  disabled={removeCollaborator.isPending}
                  className="p-1 text-gray-400 hover:text-red-600 rounded"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function LinksTab({ songId }: { songId: string }) {
  const { data, isLoading } = useShareLinks(songId);
  const createShareLink = useCreateShareLink(songId);
  const deleteShareLink = useDeleteShareLink(songId);
  const [newLinkRole, setNewLinkRole] = useState<CollaboratorRole>('viewer');
  const [copied, setCopied] = useState<string | null>(null);

  const handleCreateLink = () => {
    createShareLink.mutate({ role: newLinkRole });
  };

  const handleCopy = async (url: string, linkId: string) => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(linkId);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // Fallback
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      setCopied(linkId);
      setTimeout(() => setCopied(null), 2000);
    }
  };

  const handleDelete = (linkId: string) => {
    deleteShareLink.mutate(linkId);
  };

  const shareLinks = data?.share_links || [];

  return (
    <div className="space-y-6">
      {/* Create new link */}
      <div className="p-4 bg-gray-50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-900 mb-3">Create a new share link</h4>
        <div className="flex gap-2">
          <select
            value={newLinkRole}
            onChange={(e) => setNewLinkRole(e.target.value as CollaboratorRole)}
            className="flex-1 text-sm border border-gray-200 rounded-lg px-3 py-2"
          >
            <option value="viewer">Can view</option>
            <option value="editor">Can edit</option>
          </select>
          <button
            onClick={handleCreateLink}
            disabled={createShareLink.isPending}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
          >
            {createShareLink.isPending ? 'Creating...' : 'Create link'}
          </button>
        </div>
      </div>

      {/* Existing links */}
      {isLoading ? (
        <div className="flex items-center justify-center py-4">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
        </div>
      ) : shareLinks.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-4">
          No share links yet. Create one above.
        </p>
      ) : (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-900">Active links</h4>
          {shareLinks.map((link) => (
            <div
              key={link.id}
              className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded ${
                    link.role === 'editor'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}>
                    {link.role === 'editor' ? 'Can edit' : 'Can view'}
                  </span>
                  <span className="text-xs text-gray-500">
                    Used {link.use_count} {link.use_count === 1 ? 'time' : 'times'}
                  </span>
                </div>
                <p className="mt-1 text-xs text-gray-500 truncate">
                  {link.share_url || `${window.location.origin}/share/${link.token}`}
                </p>
              </div>
              <div className="flex items-center gap-1 ml-2">
                <button
                  onClick={() => handleCopy(
                    link.share_url || `${window.location.origin}/share/${link.token}`,
                    link.id
                  )}
                  className={`p-2 rounded-lg transition-colors ${
                    copied === link.id
                      ? 'bg-green-100 text-green-600'
                      : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  {copied === link.id ? (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                  )}
                </button>
                <button
                  onClick={() => handleDelete(link.id)}
                  disabled={deleteShareLink.isPending}
                  className="p-2 text-gray-400 hover:text-red-600 rounded-lg hover:bg-gray-100"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
