/**
 * Audio Popup Component
 *
 * Displays audio controls for a section version.
 * Allows playing, pausing, and uploading audio files.
 */

import { forwardRef } from 'react';
import { AudioFile } from '@/types/audio';

export interface AudioPopupProps {
  audioFiles: AudioFile[];
  position: { x: number; y: number };
  playingAudioId: string | null;
  isUploading: boolean;
  canUpload: boolean;
  onTogglePlay: (audioFile: AudioFile) => void;
  onDelete: (audioId: string) => void;
  onUploadClick: () => void;
}

export const AudioPopup = forwardRef<HTMLDivElement, AudioPopupProps>(
  function AudioPopup(
    { audioFiles, position, playingAudioId, isUploading, canUpload, onTogglePlay, onDelete, onUploadClick },
    ref
  ) {
    return (
      <div
        ref={ref}
        className="section-popup"
        style={{ left: position.x, top: position.y }}
      >
        <div className="section-popup-header">Audio</div>
        {audioFiles.length === 0 ? (
          <div className="section-popup-empty">No audio attached</div>
        ) : (
          <div className="section-popup-list">
            {audioFiles.map((audioFile) => (
              <div key={audioFile.id} className="section-popup-audio">
                <span className="audio-name">
                  {audioFile.display_name || audioFile.filename}
                </span>
                <div className="audio-controls">
                  <button
                    className="section-popup-item"
                    onClick={() => onTogglePlay(audioFile)}
                  >
                    {playingAudioId === audioFile.id ? '⏸ Pause' : '▶ Play'}
                  </button>
                  <button
                    className="section-popup-item danger"
                    onClick={() => onDelete(audioFile.id)}
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <button
          className="section-popup-action"
          onClick={onUploadClick}
          disabled={isUploading || !canUpload}
        >
          {isUploading ? 'Uploading...' : '+ Add audio file'}
        </button>
      </div>
    );
  }
);
