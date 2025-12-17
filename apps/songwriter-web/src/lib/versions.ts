/**
 * Section version API functions for the Songwriter app.
 */

import { get, post, put, del } from './api';
import type {
  SectionVersion,
  VersionListResponse,
  CreateVersionRequest,
  UpdateVersionRequest,
} from '@/types/song';

/**
 * List all versions for a section.
 */
export async function listVersions(
  songId: string,
  sectionId: string
): Promise<VersionListResponse> {
  return get<VersionListResponse>(
    `/songs/${songId}/sections/${sectionId}/versions/`
  );
}

/**
 * Get a specific version with all its lines.
 */
export async function getVersion(
  songId: string,
  sectionId: string,
  versionId: string
): Promise<SectionVersion> {
  return get<SectionVersion>(
    `/songs/${songId}/sections/${sectionId}/versions/${versionId}`
  );
}

/**
 * Create a new version for a section.
 * If duplicate_from_version_id is provided, copies lines from that version.
 */
export async function createVersion(
  songId: string,
  sectionId: string,
  data: CreateVersionRequest
): Promise<SectionVersion> {
  return post<SectionVersion, CreateVersionRequest>(
    `/songs/${songId}/sections/${sectionId}/versions/`,
    data
  );
}

/**
 * Update a version's metadata (name, notes).
 */
export async function updateVersion(
  songId: string,
  sectionId: string,
  versionId: string,
  data: UpdateVersionRequest
): Promise<SectionVersion> {
  return put<SectionVersion, UpdateVersionRequest>(
    `/songs/${songId}/sections/${sectionId}/versions/${versionId}`,
    data
  );
}

/**
 * Delete a version.
 * Cannot delete the last version of a section.
 */
export async function deleteVersion(
  songId: string,
  sectionId: string,
  versionId: string
): Promise<void> {
  return del(`/songs/${songId}/sections/${sectionId}/versions/${versionId}`);
}

/**
 * Duplicate a version with all its lines.
 */
export async function duplicateVersion(
  songId: string,
  sectionId: string,
  versionId: string,
  name?: string
): Promise<SectionVersion> {
  const params = new URLSearchParams();
  if (name) params.append('name', name);
  const query = params.toString() ? `?${params.toString()}` : '';

  return post<SectionVersion, Record<string, never>>(
    `/songs/${songId}/sections/${sectionId}/versions/${versionId}/duplicate${query}`,
    {}
  );
}

/**
 * Promote a version to be the main version.
 */
export async function promoteVersion(
  songId: string,
  sectionId: string,
  versionId: string
): Promise<SectionVersion> {
  return post<SectionVersion, Record<string, never>>(
    `/songs/${songId}/sections/${sectionId}/versions/${versionId}/promote`,
    {}
  );
}
