'use client';

import { useEffect, useCallback, useRef } from 'react';
import { LexicalComposer } from '@lexical/react/LexicalComposer';
import { PlainTextPlugin } from '@lexical/react/LexicalPlainTextPlugin';
import { ContentEditable } from '@lexical/react/LexicalContentEditable';
import { HistoryPlugin } from '@lexical/react/LexicalHistoryPlugin';
import { OnChangePlugin } from '@lexical/react/LexicalOnChangePlugin';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { LexicalErrorBoundary } from '@lexical/react/LexicalErrorBoundary';
import {
  $getRoot,
  $getSelection,
  $isRangeSelection,
  $isElementNode,
  $createParagraphNode,
  $createTextNode,
  KEY_ENTER_COMMAND,
  KEY_BACKSPACE_COMMAND,
  KEY_ESCAPE_COMMAND,
  COMMAND_PRIORITY_HIGH,
  EditorState,
  $setSelection,
  $createRangeSelection,
} from 'lexical';
import { $selectAll } from '@lexical/selection';
import { mergeRegister } from '@lexical/utils';

interface LexicalLineEditorProps {
  initialText: string;
  placeholder?: string;
  onTextChange: (text: string) => void;
  onEnter: (textBefore: string, textAfter: string) => void;
  onShiftEnter: () => void;
  onBackspaceAtStart: (hasContent: boolean) => void;
  onEscape: () => void;
  onBlur?: () => void;
  shouldFocus?: boolean;
  focusCursorPosition?: number;
  onFocusHandled?: () => void;
  className?: string;
}

// Plugin to handle keyboard commands
function KeyboardPlugin({
  onEnter,
  onShiftEnter,
  onBackspaceAtStart,
  onEscape,
}: {
  onEnter: (textBefore: string, textAfter: string) => void;
  onShiftEnter: () => void;
  onBackspaceAtStart: (hasContent: boolean) => void;
  onEscape: () => void;
}) {
  const [editor] = useLexicalComposerContext();

  useEffect(() => {
    return mergeRegister(
      editor.registerCommand(
        KEY_ENTER_COMMAND,
        (event: KeyboardEvent | null) => {
          if (event?.shiftKey) {
            event.preventDefault();
            onShiftEnter();
            return true;
          }

          event?.preventDefault();

          const selection = $getSelection();
          if (!$isRangeSelection(selection)) return false;

          const root = $getRoot();
          const fullText = root.getTextContent();
          const anchor = selection.anchor;
          const offset = anchor.offset;

          // Get text before and after cursor
          // For plain text, we just split at the offset
          const textBefore = fullText.substring(0, offset);
          const textAfter = fullText.substring(offset);

          onEnter(textBefore, textAfter);
          return true;
        },
        COMMAND_PRIORITY_HIGH
      ),
      editor.registerCommand(
        KEY_BACKSPACE_COMMAND,
        (event: KeyboardEvent | null) => {
          const selection = $getSelection();
          if (!$isRangeSelection(selection)) return false;

          const anchor = selection.anchor;
          const offset = anchor.offset;
          const root = $getRoot();
          const fullText = root.getTextContent();

          // Only intercept if cursor is at the very start
          if (offset === 0 && selection.isCollapsed()) {
            event?.preventDefault();
            onBackspaceAtStart(fullText.length > 0);
            return true;
          }

          return false;
        },
        COMMAND_PRIORITY_HIGH
      ),
      editor.registerCommand(
        KEY_ESCAPE_COMMAND,
        () => {
          onEscape();
          return true;
        },
        COMMAND_PRIORITY_HIGH
      )
    );
  }, [editor, onEnter, onShiftEnter, onBackspaceAtStart, onEscape]);

  return null;
}

// Plugin to handle focus and cursor positioning
function FocusPlugin({
  shouldFocus,
  focusCursorPosition,
  onFocusHandled,
}: {
  shouldFocus?: boolean;
  focusCursorPosition?: number;
  onFocusHandled?: () => void;
}) {
  const [editor] = useLexicalComposerContext();
  const hasHandledFocus = useRef(false);

  useEffect(() => {
    if (shouldFocus && !hasHandledFocus.current) {
      hasHandledFocus.current = true;

      editor.focus(() => {
        editor.update(() => {
          const root = $getRoot();
          const firstChild = root.getFirstChild();

          if (firstChild && $isElementNode(firstChild)) {
            const textContent = root.getTextContent();
            const position = Math.min(focusCursorPosition ?? 0, textContent.length);

            // Create a selection at the specified position
            const selection = $createRangeSelection();
            const textNode = firstChild.getFirstChild();

            if (textNode) {
              selection.anchor.set(textNode.getKey(), position, 'text');
              selection.focus.set(textNode.getKey(), position, 'text');
              $setSelection(selection);
            } else {
              // No text node, just select at start
              selection.anchor.set(firstChild.getKey(), 0, 'element');
              selection.focus.set(firstChild.getKey(), 0, 'element');
              $setSelection(selection);
            }
          }
        });

        // Call onFocusHandled AFTER focus completes
        onFocusHandled?.();
      });
    }
  }, [editor, shouldFocus, focusCursorPosition, onFocusHandled]);

  // Reset when shouldFocus becomes false
  useEffect(() => {
    if (!shouldFocus) {
      hasHandledFocus.current = false;
    }
  }, [shouldFocus]);

  return null;
}

// Plugin to sync external text changes
function SyncPlugin({ text }: { text: string }) {
  const [editor] = useLexicalComposerContext();
  const lastText = useRef(text);

  useEffect(() => {
    // Only update if text changed externally (not from user input)
    if (text !== lastText.current) {
      lastText.current = text;

      editor.update(() => {
        const root = $getRoot();
        const currentText = root.getTextContent();

        if (currentText !== text) {
          root.clear();
          const paragraph = $createParagraphNode();
          paragraph.append($createTextNode(text));
          root.append(paragraph);
        }
      });
    }
  }, [editor, text]);

  return null;
}

function onError(error: Error) {
  console.error('Lexical error:', error);
}

export function LexicalLineEditor({
  initialText,
  placeholder = 'Type lyrics...',
  onTextChange,
  onEnter,
  onShiftEnter,
  onBackspaceAtStart,
  onEscape,
  onBlur,
  shouldFocus,
  focusCursorPosition,
  onFocusHandled,
  className = '',
}: LexicalLineEditorProps) {
  const lastTextRef = useRef(initialText);

  const initialConfig = {
    namespace: 'LyricLineEditor',
    onError,
    editorState: () => {
      const root = $getRoot();
      const paragraph = $createParagraphNode();
      paragraph.append($createTextNode(initialText));
      root.append(paragraph);
    },
  };

  const handleChange = useCallback(
    (editorState: EditorState) => {
      editorState.read(() => {
        const root = $getRoot();
        const text = root.getTextContent();

        // Only notify if text actually changed
        if (text !== lastTextRef.current) {
          lastTextRef.current = text;
          onTextChange(text);
        }
      });
    },
    [onTextChange]
  );

  return (
    <LexicalComposer initialConfig={initialConfig}>
      <div className={`relative ${className}`}>
        <PlainTextPlugin
          contentEditable={
            <ContentEditable
              className="outline-none min-h-[1.5em] text-gray-800 dark:text-gray-200"
              onBlur={onBlur}
            />
          }
          placeholder={
            <div className="absolute top-0 left-0 text-gray-400 pointer-events-none">
              {placeholder}
            </div>
          }
          ErrorBoundary={LexicalErrorBoundary}
        />
        <OnChangePlugin onChange={handleChange} />
        <HistoryPlugin />
        <KeyboardPlugin
          onEnter={onEnter}
          onShiftEnter={onShiftEnter}
          onBackspaceAtStart={onBackspaceAtStart}
          onEscape={onEscape}
        />
        <FocusPlugin
          shouldFocus={shouldFocus}
          focusCursorPosition={focusCursorPosition}
          onFocusHandled={onFocusHandled}
        />
        <SyncPlugin text={initialText} />
      </div>
    </LexicalComposer>
  );
}
