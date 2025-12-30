'use client';

/**
 * Yjs Canvas Hook
 *
 * Provides Yjs Y.Text binding for CodeMirror collaborative editing.
 * Uses the 'canvas' field from the Yjs document for real-time text sync.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { useAuth } from '@/lib/auth-context';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8081';

// Convert HTTP URL to WebSocket URL
function getWebSocketUrl(): string {
  const url = new URL(API_BASE_URL);
  const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${url.host}`;
}

export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

export interface YjsCanvasState {
  /** The Y.Text for the canvas content */
  yText: Y.Text | null;
  /** The Yjs document */
  doc: Y.Doc | null;
  /** WebSocket provider (for awareness) */
  provider: WebsocketProvider | null;
  /** Connection status */
  status: ConnectionStatus;
  /** Whether the document has synced with the server */
  isSynced: boolean;
  /** Error message if status is 'error' */
  error: string | null;
  /** Number of connected users (including self) */
  connectedUsers: number;
  /** Reconnect manually */
  reconnect: () => void;
  /** Disconnect manually */
  disconnect: () => void;
}

export interface UseYjsCanvasOptions {
  /** Song ID to connect to */
  songId: string;
  /** Whether to auto-connect (default: true) */
  autoConnect?: boolean;
  /** Callback when document syncs */
  onSync?: (yText: Y.Text, doc: Y.Doc) => void;
  /** Callback when connection status changes */
  onStatusChange?: (status: ConnectionStatus) => void;
}

/**
 * Hook for managing Yjs collaborative editing for the canvas.
 *
 * @example
 * ```tsx
 * const { yText, provider, status } = useYjsCanvas({
 *   songId: song.id,
 *   onSync: (yText) => console.log('Canvas synced'),
 * });
 *
 * if (status === 'connected' && yText && provider) {
 *   // Use yCollab(yText, provider.awareness) in CodeMirror
 * }
 * ```
 */
export function useYjsCanvas({
  songId,
  autoConnect = true,
  onSync,
  onStatusChange,
}: UseYjsCanvasOptions): YjsCanvasState {
  const { accessToken, isAuthenticated } = useAuth();
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [isSynced, setIsSynced] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectedUsers, setConnectedUsers] = useState(0);
  const [yText, setYText] = useState<Y.Text | null>(null);

  const docRef = useRef<Y.Doc | null>(null);
  const providerRef = useRef<WebsocketProvider | null>(null);
  const mountedRef = useRef(true);

  // Update status and call callback
  const updateStatus = useCallback(
    (newStatus: ConnectionStatus) => {
      if (mountedRef.current) {
        setStatus(newStatus);
        onStatusChange?.(newStatus);
      }
    },
    [onStatusChange]
  );

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!songId || !accessToken || !isAuthenticated) {
      return;
    }

    // Clean up existing connection
    if (providerRef.current) {
      providerRef.current.destroy();
    }
    if (docRef.current) {
      docRef.current.destroy();
    }

    updateStatus('connecting');
    setError(null);
    setIsSynced(false);

    // Create new Yjs document
    const doc = new Y.Doc();
    docRef.current = doc;

    // Get the canvas Y.Text reference (but don't expose until synced)
    const canvasText = doc.getText('canvas');

    // Build WebSocket URL with token
    const wsUrl = getWebSocketUrl();
    const roomName = `${songId}/yjs`;

    try {
      // Create WebSocket provider
      const provider = new WebsocketProvider(
        `${wsUrl}/ws/songs`,
        roomName,
        doc,
        {
          params: { token: accessToken },
          connect: true,
        }
      );

      providerRef.current = provider;

      // Handle connection status
      provider.on('status', (event: { status: string }) => {
        if (!mountedRef.current) return;

        console.log('[YjsCanvas] WebSocket status:', event.status, {
          wsconnected: provider.wsconnected,
          synced: provider.synced,
        });

        if (event.status === 'connected') {
          updateStatus('connected');
        } else if (event.status === 'disconnected') {
          updateStatus('disconnected');
        }
      });

      // Handle sync - only expose yText after sync to avoid cursor position errors
      provider.on('sync', (synced: boolean) => {
        if (!mountedRef.current) return;

        console.log('[YjsCanvas] Sync event:', synced, 'canvasText.length:', canvasText.length);
        console.log('[YjsCanvas] Canvas content:', JSON.stringify(canvasText.toString().substring(0, 200)));

        if (synced) {
          // Now expose yText - CodeMirror will remount with fresh state via key prop
          setYText(canvasText);
          setIsSynced(true);
          onSync?.(canvasText, doc);
        }
      });

      // Log Y.Doc updates to see if changes are being tracked
      doc.on('update', (update: Uint8Array, origin: unknown) => {
        console.log('[YjsCanvas] Doc update:', {
          updateSize: update.length,
          origin: origin === provider ? 'remote' : origin === null ? 'local' : 'other',
          canvasLength: canvasText.length,
          wsConnected: provider.wsconnected,
        });
      });

      // Handle awareness (connected users)
      provider.awareness.on('change', () => {
        if (!mountedRef.current) return;

        const states = provider.awareness.getStates();
        setConnectedUsers(states.size);
      });

      // Handle connection error
      provider.on('connection-error', (event: Event) => {
        if (!mountedRef.current) return;

        console.error('Yjs WebSocket connection error:', event);
        setError('Connection failed');
        updateStatus('error');
      });

      // Handle connection close
      provider.on('connection-close', (event: CloseEvent | null) => {
        if (!mountedRef.current) return;

        if (event?.code === 1008) {
          setError('Authentication failed');
          updateStatus('error');
        }
      });
    } catch (err) {
      console.error('Failed to create Yjs provider:', err);
      setError(err instanceof Error ? err.message : 'Connection failed');
      updateStatus('error');
    }
  }, [songId, accessToken, isAuthenticated, updateStatus, onSync]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (providerRef.current) {
      providerRef.current.destroy();
      providerRef.current = null;
    }
    if (docRef.current) {
      docRef.current.destroy();
      docRef.current = null;
    }
    setYText(null);
    updateStatus('disconnected');
  }, [updateStatus]);

  // Reconnect
  const reconnect = useCallback(() => {
    disconnect();
    connect();
  }, [connect, disconnect]);

  // Auto-connect on mount
  useEffect(() => {
    mountedRef.current = true;

    if (autoConnect && songId && accessToken && isAuthenticated) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [autoConnect, songId, accessToken, isAuthenticated, connect, disconnect]);

  return {
    yText,
    doc: docRef.current,
    provider: providerRef.current,
    status,
    isSynced,
    error,
    connectedUsers,
    reconnect,
    disconnect,
  };
}
