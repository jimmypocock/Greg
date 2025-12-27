/**
 * API functions for the reference library.
 */

import { get, post, del, uploadFile } from './api';
import type {
  Document,
  DocumentListResponse,
  DocumentDetailResponse,
  JobCreatedResponse,
  LibraryStats,
  AskRequest,
  AskResponse,
} from '@/types/library';

/**
 * Upload a document to the reference library.
 */
export async function uploadDocument(
  file: File,
  chunkSize: number = 800
): Promise<JobCreatedResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('chunk_size', chunkSize.toString());

  return uploadFile<JobCreatedResponse>('/library/documents', formData);
}

/**
 * Process a URL and add it to the library.
 */
export async function processUrl(
  url: string,
  chunkSize: number = 800
): Promise<JobCreatedResponse> {
  return post<JobCreatedResponse, { url: string; chunk_size: number }>(
    '/library/documents/url',
    { url, chunk_size: chunkSize }
  );
}

/**
 * List all documents in the library.
 */
export async function listDocuments(): Promise<DocumentListResponse> {
  return get<DocumentListResponse>('/library/documents');
}

/**
 * Get details for a specific document.
 */
export async function getDocument(documentId: string): Promise<DocumentDetailResponse> {
  return get<DocumentDetailResponse>(`/library/documents/${documentId}`);
}

/**
 * Delete a document from the library.
 */
export async function deleteDocument(documentId: string): Promise<void> {
  await del(`/library/documents/${documentId}`);
}

/**
 * Get storage statistics for the library.
 */
export async function getLibraryStats(): Promise<LibraryStats> {
  return get<LibraryStats>('/library/stats');
}

/**
 * Ask a question about the library documents (non-streaming).
 */
export async function askQuestion(request: AskRequest): Promise<AskResponse> {
  return post<AskResponse, AskRequest>('/library/ask', {
    ...request,
    stream: false,
  });
}

/**
 * Format file size for display.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Get status badge color.
 */
export function getStatusColor(status: Document['status']): string {
  switch (status) {
    case 'ready':
      return 'bg-green-100 text-green-800';
    case 'processing':
      return 'bg-yellow-100 text-yellow-800';
    case 'pending':
      return 'bg-gray-100 text-gray-800';
    case 'failed':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
}
