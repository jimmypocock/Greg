/**
 * Song Shape types for the new song exploration experience.
 *
 * These types correspond to the backend SongShape models and API responses.
 */

/**
 * A key image or phrase discovered during exploration.
 */
export interface KeyImage {
  text: string;
  category: string; // "visual", "emotional", "temporal", or "general"
  notes?: string | null;
}

/**
 * The emotional journey of the song.
 */
export interface EmotionalArc {
  start: string;
  end: string;
  turning_point?: string | null;
  notes?: string | null;
}

/**
 * A suggested section from the song shape.
 */
export interface SuggestedSection {
  type: string; // SectionType value
  intent: string;
  key_images: string[];
}

/**
 * A reference song, artist, or influence.
 */
export interface Reference {
  name: string;
  aspect: string;
}

/**
 * The complete song shape as returned from the API.
 */
export interface SongShape {
  theme: string;
  theme_notes?: string | null;
  key_images: KeyImage[];
  emotional_arc: EmotionalArc;
  references: Reference[];
  suggested_structure: SuggestedSection[];
  raw_fragments: string[];
  conversation_summary?: string | null;
  is_ready: boolean;
}

/**
 * Request to quick-start a new song for exploration.
 */
export interface QuickStartRequest {
  title?: string;
  initial_input?: string;
}

/**
 * Response from quick-starting a new song.
 */
export interface QuickStartResponse {
  song_id: string;
  title: string;
  message: string;
}

/**
 * Request to chat with the song shaper.
 */
export interface ShapeChatRequest {
  message: string;
  conversation_history?: Array<{
    role: "user" | "assistant";
    content: string;
  }>;
  llm?: string;
}

/**
 * Response from finalizing the song shape.
 */
export interface FinalizeShapeResponse {
  song_id: string;
  sections_created: number;
  message: string;
}

/**
 * Node types for React Flow mindmap visualization.
 */
export type ShapeNodeType =
  | "theme"
  | "emotional"
  | "image"
  | "section"
  | "fragment"
  | "reference";

/**
 * Data for a shape node in the mindmap.
 */
export interface ShapeNodeData {
  label: string;
  nodeType: ShapeNodeType;
  sublabel?: string;
  category?: string;
  intent?: string;
}
