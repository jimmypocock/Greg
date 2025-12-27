/**
 * Types for the reference library feature.
 */

export interface Document {
  id: string;
  name: string;
  file_type: string;
  file_size: number;
  status: 'pending' | 'processing' | 'ready' | 'failed';
  chunk_count: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
}

export interface DocumentDetailResponse extends Document {
  extra_metadata?: Record<string, unknown>;
}

export interface JobCreatedResponse {
  job_id: string;
  status: string;
  message: string;
  websocket_url: string;
}

export interface LibraryStats {
  total_documents: number;
  total_chunks: number;
  total_size_bytes: number;
}

export interface AskRequest {
  question: string;
  document_id?: string;
  model_name?: string;
  temperature?: number;
  max_results?: number;
  stream?: boolean;
}

export interface AskResponse {
  answer: string;
  sources: Array<{
    document_id: string;
    filename: string;
    relevance_score: number;
  }>;
  chunks_used: number;
  model?: string;
  tokens_used?: number;
}
