/**
 * Audio file API functions for the Songwriter app.
 */

import { get, del, put } from './api';
import type {
  AudioFile,
  AudioFileListResponse,
  AudioUploadResponse,
  AnalysisTaskResponse,
  ApplyAnalysisResponse,
  UpdateAudioFileRequest,
} from '@/types/audio';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';

/**
 * Get the stream URL for an audio file.
 */
export function getAudioStreamUrl(songId: string, audioId: string): string {
  return `${API_BASE_URL}/songs/${songId}/audio/${audioId}/stream`;
}

/**
 * Upload an audio file for a song.
 * Optionally attach to a specific section version.
 */
export async function uploadAudioFile(
  songId: string,
  file: File,
  isReference: boolean = false,
  sectionVersionId?: string
): Promise<AudioUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('is_reference', isReference.toString());
  if (sectionVersionId) {
    formData.append('section_version_id', sectionVersionId);
  }

  const response = await fetch(`${API_BASE_URL}/songs/${songId}/audio/`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const json = JSON.parse(text);
      message = json.detail || json.message || text;
    } catch {
      // Use text as-is
    }
    throw new Error(message);
  }

  return response.json();
}

/**
 * Get audio files for a song with optional filtering.
 */
export async function getAudioFiles(
  songId: string,
  options?: {
    sectionVersionId?: string;
    songLevelOnly?: boolean;
  }
): Promise<AudioFileListResponse> {
  const params = new URLSearchParams();
  if (options?.sectionVersionId) {
    params.append('section_version_id', options.sectionVersionId);
  }
  if (options?.songLevelOnly) {
    params.append('song_level_only', 'true');
  }
  const query = params.toString() ? `?${params.toString()}` : '';
  return get<AudioFileListResponse>(`/songs/${songId}/audio/${query}`);
}

/**
 * Get a single audio file.
 */
export async function getAudioFile(songId: string, audioId: string): Promise<AudioFile> {
  return get<AudioFile>(`/songs/${songId}/audio/${audioId}`);
}

/**
 * Delete an audio file.
 */
export async function deleteAudioFile(songId: string, audioId: string): Promise<void> {
  return del(`/songs/${songId}/audio/${audioId}`);
}

/**
 * Update an audio file's metadata (display name, is_reference).
 */
export async function updateAudioFile(
  songId: string,
  audioId: string,
  data: UpdateAudioFileRequest
): Promise<AudioFile> {
  return put<AudioFile, UpdateAudioFileRequest>(`/songs/${songId}/audio/${audioId}`, data);
}

/**
 * Start analysis of an audio file.
 * Returns immediately with a task_id for tracking progress via WebSocket.
 */
export async function analyzeAudioFile(
  songId: string,
  audioId: string
): Promise<AnalysisTaskResponse> {
  const response = await fetch(`${API_BASE_URL}/songs/${songId}/audio/${audioId}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const json = JSON.parse(text);
      message = json.detail || json.message || text;
    } catch {
      // Use text as-is
    }
    throw new Error(message);
  }

  return response.json();
}

/**
 * Apply analysis results from an audio file to the song metadata.
 */
export async function applyAudioAnalysis(
  songId: string,
  audioId: string
): Promise<ApplyAnalysisResponse> {
  const response = await fetch(`${API_BASE_URL}/songs/${songId}/audio/${audioId}/apply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const text = await response.text();
    let message = text;
    try {
      const json = JSON.parse(text);
      message = json.detail || json.message || text;
    } catch {
      // Use text as-is
    }
    throw new Error(message);
  }

  return response.json();
}
