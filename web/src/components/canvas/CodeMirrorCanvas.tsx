'use client';

/**
 * CodeMirror Canvas Editor
 *
 * A document-style song editor using CodeMirror for natural text editing.
 * Supports multi-line selection, copy/paste, and floating chord annotations.
 */

import { useCallback, useMemo, useRef, useEffect, useState } from 'react';
import CodeMirror, { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { EditorView, keymap, ViewUpdate, placeholder } from '@codemirror/view';
import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
import * as Y from 'yjs';
import { yCollab } from 'y-codemirror.next';
import { WebsocketProvider } from 'y-websocket';
import { Song } from '@/types/song';
import { AudioFile } from '@/types/audio';
import { chordAnnotations, getChords } from './chordAnnotations';
import { parseDocument, ParsedDocument } from './parseDocument';
import { useVersionAudioFiles } from '@/hooks/queries/audio';
import { getAudioStreamUrl } from '@/lib/audio';

// Import extracted modules
import {
  lineTypesField,
  lineTypeGutter,
  lineTypeDecorations,
  getLineTypes,
} from './extensions';
import { sectionControlsDecorations, sectionDragDrop, backspaceToLyric, prefixDetector, parseLineTypesFromText } from './extensions';
import type { SectionReorderDetail } from './extensions';
import { VersionPopup } from './popups';
import { AudioPopup } from './popups';
import { baseTheme, canvasStyles } from './styles';
import { songToTextAndChords, SectionLineInfo } from './utils';

interface CodeMirrorCanvasProps {
  song: Song;
  onChange?: (content: string, parsed: ParsedDocument) => void;
  onSave?: (parsed: ParsedDocument) => void;
  // Yjs collaborative editing (when provided, real-time sync is enabled)
  yText?: Y.Text | null;
  provider?: WebsocketProvider | null;
  // Version callbacks (from parent, with auth context)
  onDuplicateVersion?: (sectionId: string, versionId: string) => Promise<void>;
  onSwitchVersion?: (sectionId: string, versionId: string) => Promise<void>;
  // Audio callback (from parent, with auth context)
  onUploadAudio?: (sectionId: string, versionId: string, file: File) => Promise<void>;
  isUploadingAudio?: boolean;
  // Reorder callback (from parent, with auth context)
  onReorderSections?: (sectionIds: string[]) => Promise<void>;
}

// Popup state for version/audio controls
interface PopupState {
  type: 'version' | 'audio' | null;
  lineNumber: number;
  sectionInfo: SectionLineInfo | null;
  position: { x: number; y: number };
}

export function CodeMirrorCanvas({
  song,
  onChange,
  onSave,
  yText,
  provider,
  onDuplicateVersion,
  onSwitchVersion,
  onUploadAudio,
  isUploadingAudio = false,
  onReorderSections,
}: CodeMirrorCanvasProps) {
  // Check if Yjs collaborative mode is enabled
  const isCollaborative = !!(yText && provider);
  const editorRef = useRef<ReactCodeMirrorRef>(null);
  const audioInputRef = useRef<HTMLInputElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  // Popup state for version/audio controls
  const [popup, setPopup] = useState<PopupState>({
    type: null,
    lineNumber: 0,
    sectionInfo: null,
    position: { x: 0, y: 0 },
  });

  // Currently playing audio
  const [playingAudio, setPlayingAudio] = useState<{
    audioId: string;
    audio: HTMLAudioElement;
  } | null>(null);

  // Initial content, chords, line types, and section mapping from song
  const {
    text: initialContent,
    chords: initialChords,
    lineTypes: initialLineTypes,
    sectionMap: initialSectionMap,
  } = useMemo(() => songToTextAndChords(song), [song]);

  // Track section map (updated when document changes would require re-mapping)
  const [sectionMap, setSectionMap] = useState<Map<number, SectionLineInfo>>(initialSectionMap);

  // Get current section info for the popup
  const currentSectionInfo = popup.sectionInfo;
  const currentSectionId = currentSectionInfo?.sectionId;
  const currentVersionId = currentSectionInfo?.mainVersionId;

  // Loading states for version operations
  const [isDuplicating, setIsDuplicating] = useState(false);
  const [isPromoting, setIsPromoting] = useState(false);

  // Fetch audio files for the current version when popup is open
  const { data: versionAudioFiles } = useVersionAudioFiles(song.id, currentVersionId || '');

  // Get section info for a line number
  const getSectionInfo = useCallback(
    (lineNumber: number): SectionLineInfo | null => {
      return sectionMap.get(lineNumber) || null;
    },
    [sectionMap]
  );

  // Handle version button click
  const handleVersionClick = useCallback(
    (lineNumber: number, buttonRect: DOMRect) => {
      const sectionInfo = getSectionInfo(lineNumber);
      setPopup({
        type: 'version',
        lineNumber,
        sectionInfo,
        position: { x: buttonRect.left, y: buttonRect.bottom + 4 },
      });
    },
    [getSectionInfo]
  );

  // Handle audio button click
  const handleAudioClick = useCallback(
    (lineNumber: number, buttonRect: DOMRect) => {
      const sectionInfo = getSectionInfo(lineNumber);
      setPopup({
        type: 'audio',
        lineNumber,
        sectionInfo,
        position: { x: buttonRect.left, y: buttonRect.bottom + 4 },
      });
    },
    [getSectionInfo]
  );

  // Close popup
  const closePopup = useCallback(() => {
    setPopup({ type: null, lineNumber: 0, sectionInfo: null, position: { x: 0, y: 0 } });
  }, []);

  // Create a new version by duplicating the current one (via parent callback)
  const handleDuplicateVersionClick = useCallback(async () => {
    if (!currentSectionId || !currentVersionId || !onDuplicateVersion) return;

    setIsDuplicating(true);
    try {
      await onDuplicateVersion(currentSectionId, currentVersionId);
    } catch (error) {
      console.error('Failed to duplicate version:', error);
    } finally {
      setIsDuplicating(false);
      closePopup();
    }
  }, [currentSectionId, currentVersionId, onDuplicateVersion, closePopup]);

  // Switch to a different version (via parent callback)
  const handleSwitchVersionClick = useCallback(
    async (versionId: string) => {
      if (!currentSectionId || !onSwitchVersion) return;

      setIsPromoting(true);
      try {
        await onSwitchVersion(currentSectionId, versionId);
      } catch (error) {
        console.error('Failed to switch version:', error);
      } finally {
        setIsPromoting(false);
        closePopup();
      }
    },
    [currentSectionId, onSwitchVersion, closePopup]
  );

  // Handle audio file selection (via parent callback)
  const handleAudioFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file || popup.type !== 'audio' || !currentSectionId || !currentVersionId || !onUploadAudio)
        return;

      try {
        await onUploadAudio(currentSectionId, currentVersionId, file);
      } catch (error) {
        console.error('Failed to upload audio:', error);
      }

      closePopup();
      e.target.value = ''; // Reset input
    },
    [popup.type, currentSectionId, currentVersionId, onUploadAudio, closePopup]
  );

  // Play/pause audio
  const toggleAudio = useCallback(
    (audioFile: AudioFile) => {
      if (playingAudio?.audioId === audioFile.id) {
        // Stop current audio
        playingAudio.audio.pause();
        setPlayingAudio(null);
      } else {
        // Stop any playing audio
        if (playingAudio) {
          playingAudio.audio.pause();
        }
        // Play new audio
        const audioUrl = getAudioStreamUrl(song.id, audioFile.id);
        const audio = new Audio(audioUrl);
        audio.onended = () => setPlayingAudio(null);
        audio.play();
        setPlayingAudio({ audioId: audioFile.id, audio });
      }
    },
    [playingAudio, song.id]
  );

  // Remove audio file - not implemented yet (needs parent callback)
  const handleDeleteAudio = useCallback(
    (audioId: string) => {
      if (playingAudio?.audioId === audioId) {
        playingAudio.audio.pause();
        setPlayingAudio(null);
      }
      // TODO: Add onDeleteAudio callback from parent
      console.warn('Delete audio not yet implemented in canvas mode');
    },
    [playingAudio]
  );

  // Close popup when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popup.type && popupRef.current && !popupRef.current.contains(e.target as Node)) {
        closePopup();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [popup.type, closePopup]);

  // Handle button clicks from the inline controls
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      const action = target.dataset.action;
      if (!action) return;

      const controls = target.closest('.section-inline-controls') as HTMLElement;
      if (!controls) return;

      const lineNumber = parseInt(controls.dataset.lineNumber || '0', 10);
      if (!lineNumber) return;

      const rect = target.getBoundingClientRect();

      if (action === 'version') {
        e.preventDefault();
        e.stopPropagation();
        handleVersionClick(lineNumber, rect);
      } else if (action === 'audio') {
        e.preventDefault();
        e.stopPropagation();
        handleAudioClick(lineNumber, rect);
      }
    };

    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, [handleVersionClick, handleAudioClick]);

  // Handle section reorder events from CodeMirror drag-drop
  useEffect(() => {
    const handleSectionReorder = async (e: Event) => {
      const customEvent = e as CustomEvent<SectionReorderDetail>;
      const { sourceLineNumber, targetLineNumber, insertBefore } = customEvent.detail;

      // Get section info from the line numbers
      const sourceInfo = sectionMap.get(sourceLineNumber);
      const targetInfo = sectionMap.get(targetLineNumber);

      if (!sourceInfo || !targetInfo || !onReorderSections) {
        console.warn('Cannot reorder: missing section info or callback');
        return;
      }

      // Build the new section order
      const currentOrder = song.sections.map((s) => s.id);
      const sourceIndex = currentOrder.indexOf(sourceInfo.sectionId);
      const targetIndex = currentOrder.indexOf(targetInfo.sectionId);

      if (sourceIndex === -1 || targetIndex === -1) {
        console.warn('Cannot reorder: section not found in current order');
        return;
      }

      // Remove source from its current position
      const newOrder = [...currentOrder];
      newOrder.splice(sourceIndex, 1);

      // Calculate new target index (adjusted after removal)
      let newTargetIndex = targetIndex;
      if (sourceIndex < targetIndex) {
        newTargetIndex = targetIndex - 1;
      }

      // Insert at the correct position
      if (insertBefore) {
        newOrder.splice(newTargetIndex, 0, sourceInfo.sectionId);
      } else {
        newOrder.splice(newTargetIndex + 1, 0, sourceInfo.sectionId);
      }

      // Call the parent callback to update the backend
      try {
        await onReorderSections(newOrder);
      } catch (error) {
        console.error('Failed to reorder sections:', error);
      }
    };

    document.addEventListener('section-reorder', handleSectionReorder);
    return () => document.removeEventListener('section-reorder', handleSectionReorder);
  }, [sectionMap, song.sections, onReorderSections]);

  // In collaborative mode, parse line types from Y.Text content (which contains prefixes)
  // In non-collaborative mode, use the line types from the song structure
  const effectiveLineTypes = useMemo(() => {
    if (isCollaborative && yText) {
      const content = yText.toString();
      console.log('[CodeMirror] Parsing line types from Y.Text content');
      return parseLineTypesFromText(content);
    }
    return initialLineTypes;
  }, [isCollaborative, yText, initialLineTypes]);

  // Extensions (memoize to avoid re-creating on every render)
  const extensions = useMemo(
    () => {
      const baseExtensions = [
        backspaceToLyric, // Must come before default keymap
        keymap.of([...defaultKeymap, ...historyKeymap]),
        lineTypesField.init(() => effectiveLineTypes),
        lineTypeDecorations,
        sectionControlsDecorations,
        sectionDragDrop,
        lineTypeGutter,
        prefixDetector,
        baseTheme,
        EditorView.lineWrapping,
        chordAnnotations(initialChords),
        placeholder('Write your next hit...'),
        EditorView.contentAttributes.of({ 'aria-label': 'Song editor' }),
      ];

      if (isCollaborative && yText && provider) {
        // Collaborative mode: use yCollab for real-time sync
        // yCollab handles undo/redo internally
        // Pass null for awareness to avoid cursor position errors from stale data
        // TODO: Re-enable awareness once we handle the initial sync timing issue
        console.log('[CodeMirror] Using collaborative mode with Yjs');
        return [
          ...baseExtensions,
          yCollab(yText, null),
        ];
      } else {
        // Non-collaborative mode: use local history
        return [
          history(),
          ...baseExtensions,
        ];
      }
    },
    [initialChords, effectiveLineTypes, isCollaborative, yText, provider]
  );

  // Debounce timer for auto-save
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  const handleChange = useCallback(
    (value: string, viewUpdate: ViewUpdate) => {
      // Parse the document with current chord annotations and line types
      const chords = getChords(viewUpdate.state);
      const lineTypes = viewUpdate.state.field(lineTypesField);
      const parsed = parseDocument(value, chords, lineTypes);
      onChange?.(value, parsed);

      // Auto-save after 1 second of no changes
      if (onSave) {
        setSaveStatus('idle'); // Reset while typing
        if (saveTimeoutRef.current) {
          clearTimeout(saveTimeoutRef.current);
        }
        saveTimeoutRef.current = setTimeout(() => {
          setSaveStatus('saving');
          onSave(parsed);
          // Show "saved" briefly then fade
          setTimeout(() => setSaveStatus('saved'), 200);
          setTimeout(() => setSaveStatus('idle'), 2000);
        }, 1000);
      }
    },
    [onChange, onSave]
  );

  // Clean up timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // Save on Cmd/Ctrl+S
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        // Get current editor state for chords and line types
        const view = editorRef.current?.view;
        if (view) {
          const text = view.state.doc.toString();
          const chords = getChords(view.state);
          const lineTypes = view.state.field(lineTypesField);
          const parsed = parseDocument(text, chords, lineTypes);
          onSave?.(parsed);
        }
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onSave]);

  return (
    <div className="codemirror-canvas w-full mx-auto">
      {/* Header hints */}
      <div className="mb-2 text-xs text-gray-400 dark:text-gray-500 flex gap-4 px-2">
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded font-semibold">#</code>{' '}
          section
        </span>
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded font-semibold">
            &gt;
          </code>{' '}
          chord
        </span>
        <span>
          <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded font-semibold">
            //
          </code>{' '}
          note
        </span>
      </div>

      {/* Editor */}
      <CodeMirror
        // Force remount when switching between collaborative and non-collaborative modes
        // This prevents cursor position errors from stale awareness data
        key={isCollaborative ? 'collaborative' : 'local'}
        ref={editorRef}
        // In collaborative mode, initialize with Y.Text content, then yCollab handles updates
        // In non-collaborative mode, use the initial content from the song
        value={isCollaborative ? yText.toString() : initialContent}
        extensions={extensions}
        onChange={handleChange}
        placeholder="Start writing your song...

# Verse 1
Write your first verse lyrics here

# Chorus
Your chorus goes here

> Am G C F
Add chord progressions with >"
        basicSetup={{
          lineNumbers: false,
          foldGutter: false,
          dropCursor: true,
          allowMultipleSelections: true,
          indentOnInput: false,
          bracketMatching: false,
          closeBrackets: false,
          autocompletion: false,
          highlightActiveLine: true,
          highlightSelectionMatches: false,
          searchKeymap: true,
        }}
        className="song-editor"
      />

      {/* Footer hints */}
      <div className="mt-2 text-xs text-gray-400 dark:text-gray-500 px-2 flex items-center justify-between">
        <span>Type prefix to set type · Click gutter to change type</span>
        {isCollaborative ? (
          <span className="text-green-500 flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            Live
          </span>
        ) : (
          <span
            className={`transition-opacity duration-300 ${
              saveStatus === 'idle' ? 'opacity-0' : 'opacity-100'
            }`}
          >
            {saveStatus === 'saving' && '⏳ Saving...'}
            {saveStatus === 'saved' && '✓ Saved'}
          </span>
        )}
      </div>

      {/* Hidden audio file input */}
      <input
        ref={audioInputRef}
        type="file"
        accept="audio/*"
        onChange={handleAudioFileSelect}
        className="hidden"
      />

      {/* Version popup */}
      {popup.type === 'version' && currentSectionInfo && (
        <VersionPopup
          ref={popupRef}
          versions={currentSectionInfo.versions}
          position={popup.position}
          onSwitchVersion={handleSwitchVersionClick}
          onDuplicateVersion={handleDuplicateVersionClick}
          isDuplicating={isDuplicating}
          isPromoting={isPromoting}
          canDuplicate={!!onDuplicateVersion}
        />
      )}

      {/* Audio popup */}
      {popup.type === 'audio' && currentSectionInfo && (
        <AudioPopup
          ref={popupRef}
          audioFiles={versionAudioFiles?.audio_files || []}
          position={popup.position}
          playingAudioId={playingAudio?.audioId || null}
          isUploading={isUploadingAudio}
          canUpload={!!onUploadAudio}
          onTogglePlay={toggleAudio}
          onDelete={handleDeleteAudio}
          onUploadClick={() => audioInputRef.current?.click()}
        />
      )}

      {/* CSS for line type styling */}
      <style jsx global>
        {canvasStyles}
      </style>
    </div>
  );
}

// Re-export getLineTypes for external use
export { getLineTypes };
