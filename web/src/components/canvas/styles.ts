/**
 * Canvas Editor Styles
 *
 * All CSS-in-JS styles for the CodeMirror canvas editor.
 */

import { EditorView } from '@codemirror/view';

/**
 * Base CodeMirror theme for the canvas editor.
 */
export const baseTheme = EditorView.theme({
  '&': {
    fontSize: '14px',
    fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
  },
  '.cm-content': {
    padding: '16px 0',
    minHeight: '200px',
  },
  '.cm-line': {
    padding: '2px 8px',
  },
  '.cm-gutters': {
    backgroundColor: 'transparent',
    border: 'none',
    paddingRight: '4px',
  },
  '.cm-lineType-gutter': {
    width: '24px',
    textAlign: 'center',
  },
  '.cm-lineType-gutter .cm-gutterElement': {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    padding: '2px 0',
  },
  '&.cm-focused .cm-cursor': {
    borderLeftColor: '#3b82f6',
  },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground': {
    backgroundColor: 'rgba(59, 130, 246, 0.2)',
  },
  '.cm-activeLine': {
    backgroundColor: 'rgba(59, 130, 246, 0.05)',
  },
});

/**
 * Global CSS styles for the canvas editor.
 * These are injected via styled-jsx.
 */
export const canvasStyles = `
  @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;600;700&display=swap');

  .song-editor .cm-editor {
    background: transparent;
  }
  .song-editor .cm-scroller {
    font-family: "Roboto Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
  }
  .song-editor .cm-placeholder {
    color: #9ca3af;
    font-style: italic;
  }

  /* Line type gutter icons */
  .line-type-icon {
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    user-select: none;
    opacity: 0.6;
    transition: opacity 0.15s;
    line-height: 1;
  }
  .cm-gutterElement:hover .line-type-icon {
    opacity: 1;
  }
  .cm-lineType-gutter {
    background-color: #f9fafb;
    padding: 0 4px;
  }
  .dark .cm-lineType-gutter {
    background-color: #1f2937;
  }
  .cm-lineType-gutter .cm-gutterElement {
    cursor: pointer;
  }

  /* Gutter icon colors */
  .line-type-section { color: #333333; font-weight: bold; }
  .line-type-chord { color: #2563eb; }
  .line-type-annotation { color: #6b7280; }
  .line-type-lyric { color: #9ca3af; }
  .dark .line-type-section { color: #e5e5e5; }

  /* === LINE CONTENT STYLES === */

  /* Lyric lines - default, clean look */
  .cm-line-lyric {
    color: #333333;
  }
  .dark .cm-line-lyric {
    color: #e5e5e5;
  }

  /* Section headers - bold, dark, larger */
  .cm-line-section {
    color: #333333;
    font-weight: 700;
    font-size: 1.1em;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    position: relative;
  }
  .dark .cm-line-section {
    color: #e5e5e5;
  }

  /* Chord lines - blue, monospace */
  .cm-line-chord {
    color: #2563eb;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    font-size: 0.9em;
    letter-spacing: 0.1em;
  }
  .dark .cm-line-chord {
    color: #60a5fa;
  }

  /* Annotation lines - italic, muted */
  .cm-line-annotation {
    color: #6b7280;
    font-style: italic;
    opacity: 0.8;
  }
  .dark .cm-line-annotation {
    color: #9ca3af;
  }

  /* Inline section controls (version, audio, reorder) */
  .section-inline-controls {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    display: inline-flex;
    align-items: center;
    gap: 4px;
    opacity: 0;
    transition: opacity 0.15s ease;
    background: linear-gradient(to right, transparent, white 8px);
    padding-left: 16px;
  }
  .dark .section-inline-controls {
    background: linear-gradient(to right, transparent, #1a1a1a 8px);
  }
  .cm-line:hover .section-inline-controls {
    opacity: 1;
  }
  .section-inline-btn {
    background: none;
    border: 1px solid transparent;
    padding: 2px 6px;
    font-size: 11px;
    font-family: "Roboto Mono", ui-monospace, monospace;
    font-weight: 500;
    cursor: pointer;
    border-radius: 3px;
    color: #6b7280;
    transition: all 0.15s;
    line-height: 1.2;
  }
  .section-inline-btn:hover {
    background-color: #f3f4f6;
    border-color: #e5e7eb;
    color: #333333;
  }
  /* Drag handle styling */
  .section-drag-handle {
    cursor: grab;
    letter-spacing: -2px;
    padding: 2px 4px;
    user-select: none;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
  }
  .section-drag-handle:active {
    cursor: grabbing;
  }
  .section-drag-handle:hover {
    background-color: #e5e7eb;
  }
  .dark .section-drag-handle:hover {
    background-color: #374151;
  }
  /* Version button - purple accent */
  .section-version-btn {
    color: #7c3aed;
    font-weight: 600;
  }
  .section-version-btn:hover {
    background-color: #f5f3ff;
    border-color: #ddd6fe;
  }
  /* Audio button */
  .section-audio-btn {
    font-size: 13px;
  }
  .dark .section-inline-btn {
    color: #9ca3af;
  }
  .dark .section-inline-btn:hover {
    background-color: #374151;
    border-color: #4b5563;
    color: #e5e5e5;
  }
  .dark .section-version-btn {
    color: #a78bfa;
  }
  .dark .section-version-btn:hover {
    background-color: #4c1d95;
    border-color: #6d28d9;
  }
  /* Dragging state */
  body.dragging-section .cm-line-section {
    cursor: grabbing;
  }
  /* Drop target indicator */
  .cm-line.drop-target {
    background-color: rgba(124, 58, 237, 0.1);
    outline: 2px dashed #7c3aed;
    outline-offset: -2px;
  }
  .dark .cm-line.drop-target {
    background-color: rgba(167, 139, 250, 0.15);
    outline-color: #a78bfa;
  }

  /* Section popup (versions/audio) */
  .section-popup {
    position: fixed;
    z-index: 1000;
    min-width: 200px;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    font-family: "Roboto Mono", ui-monospace, monospace;
    font-size: 12px;
    overflow: hidden;
  }
  .dark .section-popup {
    background: #1f2937;
    border-color: #374151;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }
  .section-popup-header {
    padding: 8px 12px;
    font-weight: 600;
    color: #333;
    border-bottom: 1px solid #e5e7eb;
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.05em;
  }
  .dark .section-popup-header {
    color: #e5e5e5;
    border-color: #374151;
  }
  .section-popup-empty {
    padding: 12px;
    color: #9ca3af;
    text-align: center;
    font-style: italic;
  }
  .section-popup-list {
    max-height: 200px;
    overflow-y: auto;
  }
  .section-popup-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 8px 12px;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    color: #333;
    transition: background-color 0.15s;
  }
  .section-popup-item:hover {
    background-color: #f3f4f6;
  }
  .section-popup-item.active {
    background-color: #f5f3ff;
    color: #7c3aed;
  }
  .section-popup-item.danger:hover {
    background-color: #fef2f2;
    color: #dc2626;
  }
  .dark .section-popup-item {
    color: #e5e5e5;
  }
  .dark .section-popup-item:hover {
    background-color: #374151;
  }
  .dark .section-popup-item.active {
    background-color: #4c1d95;
    color: #a78bfa;
  }
  .dark .section-popup-item.danger:hover {
    background-color: #450a0a;
    color: #f87171;
  }
  .version-name {
    font-weight: 600;
  }
  .version-date {
    font-size: 10px;
    color: #9ca3af;
  }
  .section-popup-action {
    display: block;
    width: 100%;
    padding: 10px 12px;
    background: none;
    border: none;
    border-top: 1px solid #e5e7eb;
    cursor: pointer;
    text-align: left;
    color: #7c3aed;
    font-weight: 500;
    transition: background-color 0.15s;
  }
  .section-popup-action:hover {
    background-color: #f5f3ff;
  }
  .dark .section-popup-action {
    border-color: #374151;
    color: #a78bfa;
  }
  .dark .section-popup-action:hover {
    background-color: #4c1d95;
  }
  .section-popup-audio {
    padding: 12px;
  }
  .audio-name {
    display: block;
    font-weight: 500;
    margin-bottom: 8px;
    color: #333;
    word-break: break-all;
  }
  .dark .audio-name {
    color: #e5e5e5;
  }
  .audio-controls {
    display: flex;
    gap: 8px;
  }
  .audio-controls .section-popup-item {
    padding: 6px 12px;
    border-radius: 4px;
    flex: 1;
    justify-content: center;
    border: 1px solid #e5e7eb;
  }
  .dark .audio-controls .section-popup-item {
    border-color: #374151;
  }
`;
