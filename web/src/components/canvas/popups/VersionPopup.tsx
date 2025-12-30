/**
 * Version Popup Component
 *
 * Displays version management controls for a section.
 * Allows switching between versions and creating new ones.
 */

import { forwardRef } from 'react';
import { SectionVersionSummary } from '@/types/song';

export interface VersionPopupProps {
  versions: SectionVersionSummary[];
  position: { x: number; y: number };
  onSwitchVersion: (versionId: string) => void;
  onDuplicateVersion: () => void;
  isDuplicating: boolean;
  isPromoting: boolean;
  canDuplicate: boolean;
}

export const VersionPopup = forwardRef<HTMLDivElement, VersionPopupProps>(
  function VersionPopup(
    { versions, position, onSwitchVersion, onDuplicateVersion, isDuplicating, isPromoting, canDuplicate },
    ref
  ) {
    return (
      <div
        ref={ref}
        className="section-popup"
        style={{ left: position.x, top: position.y }}
      >
        <div className="section-popup-header">Versions</div>
        {versions.length === 0 ? (
          <div className="section-popup-empty">No versions yet</div>
        ) : (
          <div className="section-popup-list">
            {versions.map((v) => (
              <button
                key={v.id}
                className={`section-popup-item ${v.is_main ? 'active' : ''}`}
                onClick={() => onSwitchVersion(v.id)}
                disabled={v.is_main || isPromoting}
              >
                <span className="version-name">
                  {v.name || `v${v.version_number}`}
                  {v.is_main && ' (current)'}
                </span>
                <span className="version-date">{v.line_count} lines</span>
              </button>
            ))}
          </div>
        )}
        <button
          className="section-popup-action"
          onClick={onDuplicateVersion}
          disabled={isDuplicating || !canDuplicate}
        >
          {isDuplicating ? 'Creating...' : '+ Duplicate to new version'}
        </button>
      </div>
    );
  }
);
