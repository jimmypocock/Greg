'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Doc, Map as YMap, Array as YArray } from 'yjs';
import { useRequireAuth } from '@/hooks/useRequireAuth';
import { useYjsSong, ConnectionStatus } from '@/hooks/useYjsSong';

const STATUS_COLORS: Record<ConnectionStatus, string> = {
  disconnected: 'bg-gray-500',
  connecting: 'bg-yellow-500',
  connected: 'bg-green-500',
  error: 'bg-red-500',
};

interface Props {
  songId: string;
}

export default function YjsTestContent({ songId }: Props) {
  const router = useRouter();
  const { isLoading: authLoading, isAuthenticated } = useRequireAuth();

  const [docContents, setDocContents] = useState<string>('');
  const [lastSync, setLastSync] = useState<Date | null>(null);

  const handleSync = useCallback((doc: Doc) => {
    setLastSync(new Date());
    updateDocContents(doc);
  }, []);

  const { doc, status, error, connectedUsers, reconnect, disconnect } = useYjsSong({
    songId,
    autoConnect: true,
    onSync: handleSync,
  });

  const updateDocContents = useCallback((yjsDoc: Doc) => {
    try {
      const meta = yjsDoc.getMap('meta');
      const sections = yjsDoc.getArray('sections');

      const contents = {
        meta: {
          id: meta.get('id'),
          title: meta.get('title'),
          key: meta.get('key'),
          tempo: meta.get('tempo'),
          time_signature: meta.get('time_signature'),
          status: meta.get('status'),
        },
        sections: sections.toArray().map((section: unknown) => {
          const s = section as YMap<unknown>;
          const lines = s.get('lines') as YArray<unknown> | undefined;
          return {
            id: s.get('id'),
            type: s.get('type'),
            number: s.get('number'),
            lines: lines?.toArray().map((line: unknown) => {
              const l = line as YMap<unknown>;
              return {
                id: l.get('id'),
                text: l.get('text'),
                line_type: l.get('line_type'),
              };
            }) || [],
          };
        }),
      };

      setDocContents(JSON.stringify(contents, null, 2));
    } catch (err) {
      setDocContents(`Error reading document: ${err}`);
    }
  }, []);

  useEffect(() => {
    if (!doc) return;

    const updateFn = () => updateDocContents(doc);

    const meta = doc.getMap('meta');
    meta.observe(updateFn);

    const sections = doc.getArray('sections');
    sections.observeDeep(updateFn);

    updateDocContents(doc);

    return () => {
      meta.unobserve(updateFn);
      sections.unobserveDeep(updateFn);
    };
  }, [doc, updateDocContents]);

  const handleUpdateTitle = useCallback(() => {
    if (!doc) return;

    const meta = doc.getMap('meta');
    const currentTitle = meta.get('title') as string || '';
    const newTitle = prompt('Enter new title:', currentTitle);
    if (newTitle !== null) {
      meta.set('title', newTitle);
    }
  }, [doc]);

  const handleAddLine = useCallback(() => {
    if (!doc) return;

    const sections = doc.getArray('sections');
    if (sections.length === 0) {
      alert('No sections in document');
      return;
    }

    const firstSection = sections.get(0) as YMap<unknown>;
    const lines = firstSection.get('lines') as YArray<unknown>;
    if (!lines) {
      alert('Section has no lines array');
      return;
    }

    const newLineText = prompt('Enter new line text:', 'New line from test');
    if (newLineText !== null) {
      const newLine = new YMap();
      newLine.set('id', crypto.randomUUID());
      newLine.set('text', newLineText);
      newLine.set('line_type', 'LYRIC');
      newLine.set('chords', new YArray());
      lines.push([newLine]);
    }
  }, [doc]);

  if (authLoading) {
    return <div>Loading auth...</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <button
            onClick={() => router.push(`/songs/${songId}`)}
            className="text-blue-500 hover:underline mb-4 block"
          >
            &larr; Back to song
          </button>
          <h1 className="text-2xl font-bold text-gray-900">Yjs Connection Test</h1>
          <p className="text-gray-500 mt-1">
            Song ID: <code className="bg-gray-200 px-2 py-1 rounded">{songId}</code>
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Connection Status</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-500">Status</label>
              <div className="flex items-center gap-2 mt-1">
                <span className={`w-3 h-3 rounded-full ${STATUS_COLORS[status]}`} />
                <span className="font-medium text-gray-900 capitalize">{status}</span>
              </div>
            </div>
            <div>
              <label className="text-sm text-gray-500">Connected Users</label>
              <div className="font-medium text-gray-900 mt-1">{connectedUsers}</div>
            </div>
            <div>
              <label className="text-sm text-gray-500">Last Sync</label>
              <div className="font-medium text-gray-900 mt-1">
                {lastSync ? lastSync.toLocaleTimeString() : 'Never'}
              </div>
            </div>
            <div>
              <label className="text-sm text-gray-500">Error</label>
              <div className="font-medium text-red-500 mt-1">{error || 'None'}</div>
            </div>
          </div>
          <div className="flex gap-4 mt-6">
            <button
              onClick={reconnect}
              disabled={status === 'connecting'}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
            >
              Reconnect
            </button>
            <button
              onClick={disconnect}
              disabled={status === 'disconnected'}
              className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 disabled:opacity-50"
            >
              Disconnect
            </button>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Test Actions</h2>
          <div className="flex gap-4">
            <button
              onClick={handleUpdateTitle}
              disabled={status !== 'connected'}
              className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600 disabled:opacity-50"
            >
              Update Title
            </button>
            <button
              onClick={handleAddLine}
              disabled={status !== 'connected'}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50"
            >
              Add Line to First Section
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-4">
            Open this page in another browser window to test real-time sync.
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Document Contents</h2>
          <pre className="bg-gray-100 p-4 rounded overflow-auto max-h-96 text-sm text-gray-800">
            {docContents || 'No document loaded'}
          </pre>
        </div>
      </div>
    </div>
  );
}
