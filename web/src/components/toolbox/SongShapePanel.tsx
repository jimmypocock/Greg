'use client';

import { Song, SongNote, NoteType } from '@/types';

interface SongShapePanelProps {
  song: Song;
}

/**
 * Displays the song's "shape" data - theme, key images, emotional arc, and fragments.
 * This data is created by the AI shaper during new song exploration.
 */
export function SongShapePanel({ song }: SongShapePanelProps) {
  const notes = song.song_notes || [];

  // Extract shape-related notes
  const themeNote = notes.find(n => n.note_type === NoteType.THEME);
  const arcNote = notes.find(n => n.note_type === NoteType.EMOTIONAL_ARC);
  const keyImages = notes.filter(n => n.note_type === NoteType.KEY_IMAGE);
  const references = notes.filter(n => n.note_type === NoteType.REFERENCE);
  const fragments = notes.filter(n => n.note_type === NoteType.FRAGMENT);

  // Parse emotional arc
  const parseArc = (content: string) => {
    const lines: Record<string, string> = {};
    content.split('\n').forEach(line => {
      if (line.startsWith('Start:')) lines.start = line.replace('Start:', '').trim();
      if (line.startsWith('End:')) lines.end = line.replace('End:', '').trim();
      if (line.startsWith('Turning Point:')) lines.turningPoint = line.replace('Turning Point:', '').trim();
    });
    return lines;
  };

  const arc = arcNote ? parseArc(arcNote.content) : null;

  // Check if we have any shape data
  const hasShapeData = themeNote || arcNote || keyImages.length > 0 || references.length > 0 || fragments.length > 0;

  if (!hasShapeData) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-gray-400">
        <svg className="w-8 h-8 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <p className="text-sm">No song shape data yet.</p>
        <p className="text-xs mt-1">Chat with the AI to explore your song idea!</p>
      </div>
    );
  }

  return (
    <div className="p-3 space-y-4">
      {/* Theme */}
      {themeNote && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">
            Theme
          </h4>
          <p className="text-sm text-gray-900 dark:text-white">
            {themeNote.content.split('\n\n')[0]}
          </p>
          {themeNote.content.includes('\n\n') && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {themeNote.content.split('\n\n')[1]}
            </p>
          )}
        </div>
      )}

      {/* Emotional Arc */}
      {arc && (arc.start || arc.end) && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Emotional Arc
          </h4>
          <div className="flex items-center gap-2 text-sm">
            {arc.start && (
              <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded text-xs">
                {arc.start}
              </span>
            )}
            {arc.turningPoint && (
              <>
                <span className="text-gray-400">→</span>
                <span className="px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded text-xs">
                  {arc.turningPoint}
                </span>
              </>
            )}
            {arc.end && (
              <>
                <span className="text-gray-400">→</span>
                <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded text-xs">
                  {arc.end}
                </span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Key Images */}
      {keyImages.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Key Images
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {keyImages.map(note => {
              // Extract category from title like "Key Image (visual)"
              const category = note.title?.match(/\(([^)]+)\)/)?.[1] || 'general';
              const categoryColors: Record<string, string> = {
                visual: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
                emotional: 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300',
                temporal: 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-700 dark:text-cyan-300',
                metaphor: 'bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300',
                general: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300',
              };
              return (
                <span
                  key={note.id}
                  className={`px-2 py-0.5 rounded text-xs ${categoryColors[category] || categoryColors.general}`}
                  title={category}
                >
                  {note.content}
                </span>
              );
            })}
          </div>
        </div>
      )}

      {/* References */}
      {references.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            References
          </h4>
          <ul className="space-y-1">
            {references.map(note => {
              const [name, aspect] = note.content.split(' - ');
              return (
                <li key={note.id} className="text-sm text-gray-700 dark:text-gray-300">
                  <span className="font-medium">{name}</span>
                  {aspect && (
                    <span className="text-gray-500 dark:text-gray-400"> - {aspect}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Fragments */}
      {fragments.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">
            Captured Fragments
          </h4>
          <ul className="space-y-1.5">
            {fragments.map(note => (
              <li
                key={note.id}
                className="text-sm text-gray-600 dark:text-gray-300 italic border-l-2 border-gray-300 dark:border-gray-600 pl-2"
              >
                "{note.content}"
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
