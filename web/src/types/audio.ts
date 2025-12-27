/**
 * Audio file types for the Songwriter app.
 */

export enum AnalysisStatus {
  PENDING = 'pending',
  ANALYZING = 'analyzing',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

export interface ChordDetection {
  start: number;
  end: number;
  chord: string;
}

export interface AudioFile {
  id: string;
  song_id: string;
  section_version_id: string | null;
  filename: string;
  display_name: string | null;
  mime_type: string;
  file_size_bytes: number;
  duration_seconds: number | null;
  detected_tempo: number | null;
  detected_key: string | null;
  detected_time_signature: string | null;
  confidence_tempo: number | null;
  confidence_key: number | null;
  confidence_time_signature: number | null;
  detected_chords: ChordDetection[] | null;
  beat_positions: number[] | null;
  analysis_status: AnalysisStatus;
  analysis_error: string | null;
  is_reference: boolean;
  created_at: string;
  updated_at: string;
}

export interface UpdateAudioFileRequest {
  display_name?: string;
  is_reference?: boolean;
}

export interface AudioFileListResponse {
  audio_files: AudioFile[];
  total: number;
}

export interface AudioUploadResponse {
  audio_file: AudioFile;
  message: string;
}

export interface AnalysisTaskResponse {
  task_id: string;
  audio_file_id: string;
  message: string;
  websocket_url: string;
}

export interface ApplyAnalysisResponse {
  message: string;
  tempo_applied: number | null;
  key_applied: string | null;
}

// WebSocket event types for audio analysis
export type AudioEventType =
  | 'audio.started'
  | 'audio.analyzing'
  | 'audio.completed'
  | 'audio.failed';

export interface AudioEvent {
  event: AudioEventType;
  data: AudioEventData;
  timestamp?: string;
}

export interface AudioEventData {
  task_id: string;
  audio_file_id: string;
  message?: string;
  stage?: string;
  progress?: number;
  tempo?: number;
  tempo_confidence?: number;
  key?: string;
  key_confidence?: number;
  duration_seconds?: number;
  time_signature?: string;
  time_signature_confidence?: number;
  chord_count?: number;
  beat_count?: number;
  error?: string;
}
