'use client';

import { useEffect, useState, useRef } from 'react';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { useAuth } from '@/lib/auth-context';
import { EditorState } from 'prosemirror-state';
import { EditorView } from 'prosemirror-view';
import { ySyncPlugin } from 'y-prosemirror';
import { songSchema } from '@/components/canvas/schema';

const SONG_ID = '166cd349-42c0-452f-8ad3-bb1d3cf6b5db';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';

function getWebSocketUrl(): string {
  const url = new URL(API_BASE_URL);
  const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${url.host}`;
}

// Create an EMPTY local Yjs doc - let ProseMirror/ySyncPlugin populate it
function createEmptyLocalDoc(): Y.Doc {
  const doc = new Y.Doc();
  doc.getXmlFragment('prosemirror'); // Just create the fragment, don't populate
  return doc;
}

export default function TestYjsPage() {
  const { accessToken, isAuthenticated } = useAuth();
  const [status, setStatus] = useState('waiting');
  const [xmlContent, setXmlContent] = useState<string>('');
  const [detailedContent, setDetailedContent] = useState<string>('');
  const [pmDocJson, setPmDocJson] = useState<string>('');
  const [localXmlContent, setLocalXmlContent] = useState<string>('');
  const [localDetailedContent, setLocalDetailedContent] = useState<string>('');
  const editorRef = useRef<HTMLDivElement>(null);
  const localEditorRef = useRef<HTMLDivElement>(null);
  const serverFragmentRef = useRef<Y.XmlFragment | null>(null);
  const localFragmentRef = useRef<Y.XmlFragment | null>(null);
  const serverViewRef = useRef<EditorView | null>(null);

  // Manual refresh function
  const refreshDisplay = () => {
    // Local
    if (localFragmentRef.current) {
      const fragment = localFragmentRef.current;
      const xml = fragment.toArray().map((item: unknown) => {
        if (item instanceof Y.XmlElement) return elementToString(item);
        if (item instanceof Y.XmlText) return item.toString();
        return String(item);
      }).join('\n');
      setLocalXmlContent(xml || '(empty)');

      const detailed = fragment.toArray().map((item: unknown) => {
        if (item instanceof Y.XmlElement) return elementToDetailedString(item);
        return `Unknown: ${typeof item}`;
      }).join('\n');
      setLocalDetailedContent(detailed || '(no children)');
    }

    // Server
    if (serverFragmentRef.current) {
      const fragment = serverFragmentRef.current;
      const xml = fragment.toArray().map((item: unknown) => {
        if (item instanceof Y.XmlElement) return elementToString(item);
        if (item instanceof Y.XmlText) return item.toString();
        return String(item);
      }).join('\n');
      setXmlContent(xml || '(empty)');

      const detailed = fragment.toArray().map((item: unknown) => {
        if (item instanceof Y.XmlElement) return elementToDetailedString(item);
        return `Unknown: ${typeof item}`;
      }).join('\n');
      setDetailedContent(detailed || '(no children)');
    }

    // ProseMirror doc JSON
    if (serverViewRef.current) {
      setPmDocJson(JSON.stringify(serverViewRef.current.state.doc.toJSON(), null, 2));
    }
  };

  // Test with LOCAL Yjs doc (no server) - start empty, let user type
  useEffect(() => {
    if (!localEditorRef.current) return;

    const localDoc = createEmptyLocalDoc();
    const localFragment = localDoc.getXmlFragment('prosemirror');
    localFragmentRef.current = localFragment;

    // Create ProseMirror with empty Yjs doc and initial doc from schema
    let localView: EditorView | null = null;
    try {
      // Create initial doc structure
      const initialDoc = songSchema.node('doc', null, [
        songSchema.node('part', { id: 'test', type: 'VERSE', mainVersionId: null }, [
          songSchema.node('label', null, [songSchema.text('Verse 1')]),
          songSchema.node('line', { lineType: 'LYRIC' }, [songSchema.text('Type here...')]),
        ]),
      ]);

      const state = EditorState.create({
        doc: initialDoc,
        schema: songSchema,
        plugins: [ySyncPlugin(localFragment)],
      });

      localView = new EditorView(localEditorRef.current, { state });
    } catch (err) {
      console.error('Local editor error:', err);
    }

    return () => {
      if (localView) localView.destroy();
      localDoc.destroy();
      localFragmentRef.current = null;
    };
  }, []);

  // Test with SERVER Yjs doc
  useEffect(() => {
    if (!accessToken || !isAuthenticated) {
      setStatus('not authenticated');
      return;
    }

    setStatus('connecting...');

    const doc = new Y.Doc();
    const wsUrl = getWebSocketUrl();
    const roomName = `${SONG_ID}/yjs`;

    const provider = new WebsocketProvider(
      `${wsUrl}/ws/songs`,
      roomName,
      doc,
      { params: { token: accessToken }, connect: true }
    );

    const pmFragment = doc.getXmlFragment('prosemirror');
    serverFragmentRef.current = pmFragment;
    let view: EditorView | null = null;

    provider.on('status', (event: { status: string }) => {
      setStatus(`ws: ${event.status}`);
    });

    provider.on('sync', (synced: boolean) => {
      if (synced) {
        setStatus('synced');

        // Create ProseMirror EditorState with ySyncPlugin
        if (editorRef.current && !view) {
          try {
            const state = EditorState.create({
              schema: songSchema,
              plugins: [ySyncPlugin(pmFragment)],
            });

            view = new EditorView(editorRef.current, { state });
            serverViewRef.current = view;

            // Show initial doc JSON
            setPmDocJson(JSON.stringify(state.doc.toJSON(), null, 2));
          } catch (err) {
            console.error('Server editor error:', err);
          }
        }
      }
    });

    return () => {
      if (view) view.destroy();
      serverViewRef.current = null;
      provider.destroy();
      doc.destroy();
      serverFragmentRef.current = null;
    };
  }, [accessToken, isAuthenticated]);

  return (
    <div style={{ padding: 20, fontFamily: 'monospace' }}>
      <h1>Yjs Test</h1>
      <button onClick={refreshDisplay} style={{ padding: '10px 20px', marginBottom: 20, fontSize: 14 }}>
        Refresh Yjs Display
      </button>

      <div style={{ display: 'flex', gap: 20 }}>
        <div style={{ flex: 1 }}>
          <h2>LOCAL Yjs (created in browser)</h2>
          <h3>XmlFragment:</h3>
          <pre style={{ background: '#f0f0f0', padding: 10, overflow: 'auto', maxHeight: 120, fontSize: 11 }}>
            {localXmlContent || '(empty)'}
          </pre>
          <h3>Detailed Structure:</h3>
          <pre style={{ background: '#e8e8e8', padding: 10, overflow: 'auto', maxHeight: 150, fontSize: 10 }}>
            {localDetailedContent || '(waiting...)'}
          </pre>
          <h3>Editor:</h3>
          <div
            ref={localEditorRef}
            style={{ border: '2px solid green', minHeight: 80, padding: 10, background: 'white' }}
          />
        </div>

        <div style={{ flex: 1 }}>
          <h2>SERVER Yjs (from backend)</h2>
          <p><strong>Status:</strong> {status}</p>
          <h3>XmlFragment:</h3>
          <pre style={{ background: '#f0f0f0', padding: 10, overflow: 'auto', maxHeight: 100, fontSize: 10 }}>
            {xmlContent || '(empty)'}
          </pre>
          <h3>Detailed Structure:</h3>
          <pre style={{ background: '#ffe8e8', padding: 10, overflow: 'auto', maxHeight: 120, fontSize: 9 }}>
            {detailedContent || '(waiting...)'}
          </pre>
          <h3>ProseMirror Doc JSON:</h3>
          <pre style={{ background: '#e0e0ff', padding: 10, overflow: 'auto', maxHeight: 120, fontSize: 9 }}>
            {pmDocJson || '(waiting...)'}
          </pre>
          <h3>Editor:</h3>
          <div
            ref={editorRef}
            style={{ border: '2px solid blue', minHeight: 80, padding: 10, background: 'white' }}
          />
        </div>
      </div>
    </div>
  );
}

function elementToString(el: Y.XmlElement, indent = 0): string {
  const pad = '  '.repeat(indent);
  const tag = el.nodeName;
  const attrs = Object.entries(el.getAttributes())
    .map(([k, v]) => `${k}="${v}"`)
    .join(' ');

  const children = el.toArray().map((child: unknown) => {
    if (child instanceof Y.XmlElement) {
      return elementToString(child, indent + 1);
    } else if (child instanceof Y.XmlText) {
      return '  '.repeat(indent + 1) + child.toString();
    }
    return '  '.repeat(indent + 1) + String(child);
  }).join('\n');

  if (children) {
    return `${pad}<${tag}${attrs ? ' ' + attrs : ''}>\n${children}\n${pad}</${tag}>`;
  }
  return `${pad}<${tag}${attrs ? ' ' + attrs : ''} />`;
}

// Detailed structure showing types
function elementToDetailedString(el: Y.XmlElement, indent = 0): string {
  const pad = '  '.repeat(indent);
  const tag = el.nodeName;
  const attrs = el.getAttributes();

  let result = `${pad}XmlElement("${tag}") attrs=${JSON.stringify(attrs)}\n`;

  const children = el.toArray();
  result += `${pad}  children (${children.length}):\n`;

  children.forEach((child: unknown, i: number) => {
    if (child instanceof Y.XmlElement) {
      result += elementToDetailedString(child, indent + 2);
    } else if (child instanceof Y.XmlText) {
      const text = child.toString();
      result += `${pad}    [${i}] XmlText: "${text}" (length=${text.length})\n`;
    } else {
      result += `${pad}    [${i}] Unknown: ${typeof child} = ${String(child)}\n`;
    }
  });

  return result;
}
