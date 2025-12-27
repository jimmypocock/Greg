'use client';

import { useState, useCallback } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AuthGuard } from '@/components/auth/AuthGuard';
import { UserMenu } from '@/components/auth/UserMenu';
import {
  listDocuments,
  uploadDocument,
  deleteDocument,
  formatFileSize,
  getStatusColor,
} from '@/lib/library';
import type { Document } from '@/types/library';

export default function LibraryPage() {
  return (
    <AuthGuard>
      <LibraryContent />
    </AuthGuard>
  );
}

function LibraryContent() {
  const queryClient = useQueryClient();
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['library-documents'],
    queryFn: listDocuments,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['library-documents'] });
      setUploadError(null);
    },
    onError: (err: Error) => {
      setUploadError(err.message);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['library-documents'] });
    },
  });

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        uploadMutation.mutate(files[0]);
      }
    },
    [uploadMutation]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        uploadMutation.mutate(files[0]);
      }
    },
    [uploadMutation]
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="flex items-center gap-2">
                <svg
                  className="h-7 w-7 text-indigo-600"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
                  />
                </svg>
                <span className="text-2xl font-bold text-gray-900">Songwriter</span>
              </Link>
              <span className="text-gray-400">/</span>
              <h1 className="text-xl font-semibold text-gray-700">Reference Library</h1>
            </div>
            <UserMenu />
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Upload Area */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            isDragging
              ? 'border-indigo-500 bg-indigo-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
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
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <div className="mt-4">
            <label className="cursor-pointer">
              <span className="text-indigo-600 hover:text-indigo-500 font-medium">
                Upload a file
              </span>
              <input
                type="file"
                className="hidden"
                onChange={handleFileSelect}
                accept=".pdf,.txt,.md,.docx,.csv,.xlsx,.png,.jpg,.jpeg"
              />
            </label>
            <span className="text-gray-500"> or drag and drop</span>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            PDF, TXT, Markdown, Word, Excel, CSV, or images
          </p>

          {uploadMutation.isPending && (
            <div className="mt-4 flex items-center justify-center gap-2 text-indigo-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-600"></div>
              <span>Uploading...</span>
            </div>
          )}

          {uploadError && (
            <p className="mt-4 text-sm text-red-600">{uploadError}</p>
          )}
        </div>

        {/* Documents List */}
        <div className="mt-8">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Your Documents {data?.documents && `(${data.documents.length})`}
          </h2>

          {isLoading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
              <p className="mt-2 text-sm text-gray-500">Loading documents...</p>
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm text-red-700">
                {error instanceof Error ? error.message : 'Failed to load documents'}
              </p>
            </div>
          ) : data?.documents.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>No documents yet. Upload your first reference document above.</p>
              <p className="mt-2 text-sm">
                Add chord charts, music theory notes, lyrics for inspiration, or any reference material.
              </p>
            </div>
          ) : (
            <div className="bg-white shadow overflow-hidden rounded-lg">
              <ul className="divide-y divide-gray-200">
                {data?.documents.map((doc) => (
                  <DocumentRow
                    key={doc.id}
                    document={doc}
                    onDelete={() => deleteMutation.mutate(doc.id)}
                    isDeleting={deleteMutation.isPending}
                  />
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Help Text */}
        <div className="mt-8 bg-gray-100 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-2">
            What can you do with the Reference Library?
          </h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Upload chord charts, music theory docs, and songwriting books</li>
            <li>• Store lyrics from songs that inspire you</li>
            <li>• Ask questions about your documents using AI</li>
            <li>• Search across all your reference materials while writing</li>
          </ul>
        </div>
      </main>
    </div>
  );
}

function DocumentRow({
  document,
  onDelete,
  isDeleting,
}: {
  document: Document;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <li className="px-4 py-4 flex items-center justify-between">
      <div className="flex items-center min-w-0 gap-4">
        <div className="flex-shrink-0">
          <FileIcon fileType={document.file_type} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-900 truncate">{document.name}</p>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-gray-500">{formatFileSize(document.file_size)}</span>
            <span className="text-xs text-gray-500">
              {document.chunk_count} chunk{document.chunk_count !== 1 ? 's' : ''}
            </span>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${getStatusColor(
                document.status
              )}`}
            >
              {document.status}
            </span>
          </div>
          {document.error_message && (
            <p className="mt-1 text-xs text-red-600">{document.error_message}</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {showConfirm ? (
          <>
            <button
              onClick={() => {
                onDelete();
                setShowConfirm(false);
              }}
              disabled={isDeleting}
              className="text-xs px-2 py-1 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              {isDeleting ? 'Deleting...' : 'Confirm'}
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              className="text-xs px-2 py-1 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            onClick={() => setShowConfirm(true)}
            className="text-gray-400 hover:text-red-600"
            title="Delete document"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        )}
      </div>
    </li>
  );
}

function FileIcon({ fileType }: { fileType: string }) {
  const iconClass = "h-8 w-8";

  switch (fileType.toLowerCase()) {
    case 'pdf':
      return (
        <svg className={`${iconClass} text-red-500`} fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 2l5 5h-5V4zM8.5 13h1.2l.6 2.4.6-2.4h1.2L10.8 17H9.6l-.6-2.4-.6 2.4H7.2l-1.2-4zm4.5 0h2.4c.6 0 1.2.4 1.2 1s-.6 1-1.2 1H14v2h-1v-4z"/>
        </svg>
      );
    case 'txt':
    case 'md':
    case 'markdown':
      return (
        <svg className={`${iconClass} text-gray-500`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      );
    case 'docx':
      return (
        <svg className={`${iconClass} text-blue-500`} fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 2l5 5h-5V4zM9 17H7l1.5-6L10 17H9zm2 0l1.5-6 1.5 6h-1z"/>
        </svg>
      );
    case 'xlsx':
    case 'xls':
    case 'csv':
      return (
        <svg className={`${iconClass} text-green-500`} fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm-1 2l5 5h-5V4zM7 13h2v2H7v-2zm0 3h2v2H7v-2zm3-3h2v2h-2v-2zm0 3h2v2h-2v-2zm3-3h2v2h-2v-2zm0 3h2v2h-2v-2z"/>
        </svg>
      );
    case 'png':
    case 'jpg':
    case 'jpeg':
      return (
        <svg className={`${iconClass} text-purple-500`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      );
    default:
      return (
        <svg className={`${iconClass} text-gray-400`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
      );
  }
}
