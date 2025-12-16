/**
 * Song types matching the Songwriter API.
 */

export enum SectionType {
  INTRO = 'intro',
  VERSE = 'verse',
  PRE_CHORUS = 'pre-chorus',
  CHORUS = 'chorus',
  POST_CHORUS = 'post-chorus',
  BRIDGE = 'bridge',
  OUTRO = 'outro',
  INSTRUMENTAL = 'instrumental',
  SOLO = 'solo',
  BREAKDOWN = 'breakdown',
  OTHER = 'other',
}

export enum SongStatus {
  IDEA = 'idea',
  DRAFT = 'draft',
  IN_PROGRESS = 'in_progress',
  REVIEW = 'review',
  FINISHED = 'finished',
}

export enum NoteType {
  IDEA = 'IDEA',
  INSPIRATION = 'INSPIRATION',
  REFERENCE = 'REFERENCE',
  CONTEXT = 'CONTEXT',
  TODO = 'TODO',
  FEEDBACK = 'FEEDBACK',
  OTHER = 'OTHER',
}

export interface ChordPlacement {
  id: string;
  chord: string;
  position: number;
}

export interface Line {
  id: string;
  text: string;
  order: number;
  notes?: string | null;
  chords: ChordPlacement[];
}

export interface Section {
  id: string;
  song_id: string;
  type: SectionType;
  number?: number;
  order: number;
  lines: Line[];
  notes?: string | null;
  created_at: string;
}

export interface SongNote {
  id: string;
  song_id: string;
  section_id?: string | null;
  note_type: NoteType;
  title?: string | null;
  content: string;
  is_resolved: boolean;
  created_at: string;
  updated_at: string;
}

export interface Song {
  id: string;
  title: string;
  raw_input?: string;
  key?: string;
  tempo?: number;
  time_signature: string;
  feel?: string;
  sections: Section[];
  status: SongStatus;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface SongListItem {
  id: string;
  title: string;
  status: SongStatus;
  key?: string;
  tempo?: number;
  section_count: number;
  created_at: string;
  updated_at: string;
}

export interface SongListResponse {
  songs: SongListItem[];
  total: number;
}

// Suggestion types (from AI structure suggestion - no IDs yet)
export interface SuggestionLine {
  text: string;
  chords?: { chord: string; position: number }[];
  notes?: string | null;
}

export interface SuggestionSection {
  type: SectionType;
  number?: number | null;
  lines: SuggestionLine[];
  notes?: string | null;
}

export interface StructureSuggestion {
  sections: SuggestionSection[];
  confidence: number;
  reasoning?: string;
}

// Request types
export interface SongCreateRequest {
  title: string;
  raw_input: string;
  key?: string;
  tempo?: number;
  time_signature?: string;
  feel?: string;
  notes?: string;
}

export interface SongUpdateRequest {
  title?: string;
  key?: string;
  tempo?: number;
  time_signature?: string;
  feel?: string;
  status?: SongStatus;
  notes?: string;
}

export interface MarkdownInput {
  content: string;
}

export interface AddChordRequest {
  section_id: string;
  line_id: string;
  chord: string;
  position: number;
}

export interface RemoveChordRequest {
  section_id: string;
  line_id: string;
  position: number;
}

export interface AddLineRequest {
  section_id: string;
  text: string;
  after_line_id?: string;
}

export interface UpdateLineRequest {
  section_id: string;
  line_id: string;
  text: string;
}

export interface AddSectionRequest {
  type: SectionType;
  number?: number;
  after_section_id?: string;
}

export interface ApplyStructureRequest {
  sections: SuggestionSection[];
}

// Song Notes request/response types

export interface SongNoteCreateRequest {
  note_type?: NoteType;
  content: string;
  title?: string;
  section_id?: string;
}

export interface SongNoteUpdateRequest {
  note_type?: NoteType;
  content?: string;
  title?: string;
  is_resolved?: boolean;
}

export interface SongNotesListResponse {
  notes: SongNote[];
  total: number;
}

export interface ContextResponse {
  context: string;
}
