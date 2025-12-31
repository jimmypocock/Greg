'use client';

/**
 * Yjs ProseMirror Hook
 *
 * Provides Yjs Y.XmlFragment binding for ProseMirror collaborative editing.
 * Uses the 'prosemirror' field from the Yjs document for real-time block sync.
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

export interface YjsProseMirrorState {
  /** The Y.XmlFragment for the prosemirror content */
  yXmlFragment: Y.XmlFragment | null;
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

export interface UseYjsProseMirrorOptions {
  /** Song ID to connect to */
  songId: string;
  /** Whether to auto-connect (default: true) */
  autoConnect?: boolean;
  /** Callback when document syncs - called synchronously, use for editor creation */
  onSync?: (yXmlFragment: Y.XmlFragment, doc: Y.Doc) => void;
  /** Callback when connection status changes */
  onStatusChange?: (status: ConnectionStatus) => void;
}

/**
 * Hook for managing Yjs collaborative editing with ProseMirror.
 */
export function useYjsProseMirror({
  songId,
  autoConnect = true,
  onSync,
  onStatusChange,
}: UseYjsProseMirrorOptions): YjsProseMirrorState {
  const { accessToken, isAuthenticated } = useAuth();
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [isSynced, setIsSynced] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectedUsers, setConnectedUsers] = useState(0);
  const [yXmlFragment, setYXmlFragment] = useState<Y.XmlFragment | null>(null);

  const docRef = useRef<Y.Doc | null>(null);
  const providerRef = useRef<WebsocketProvider | null>(null);
  const mountedRef = useRef(true);

  // Use refs for callbacks to avoid effect re-runs
  const onSyncRef = useRef(onSync);
  const onStatusChangeRef = useRef(onStatusChange);
  onSyncRef.current = onSync;
  onStatusChangeRef.current = onStatusChange;

  // Disconnect function (stable - no dependencies)
  const disconnect = useCallback(() => {
    if (providerRef.current) {
      providerRef.current.destroy();
      providerRef.current = null;
    }
    if (docRef.current) {
      docRef.current.destroy();
      docRef.current = null;
    }
    setYXmlFragment(null);
    setStatus('disconnected');
    setIsSynced(false);
  }, []);

  // Connect function (stable - uses refs for callbacks)
  const connect = useCallback(() => {
    // These are read at call time, not captured in closure
    const token = accessToken;
    const authenticated = isAuthenticated;

    if (!songId || !token || !authenticated) {
      return;
    }

    // Clean up existing connection
    disconnect();

    setStatus('connecting');
    onStatusChangeRef.current?.('connecting');
    setError(null);
    setIsSynced(false);

    // Create new Yjs document
    const doc = new Y.Doc();
    docRef.current = doc;

    // Get the prosemirror XmlFragment reference
    const pmFragment = doc.getXmlFragment('prosemirror');

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
          params: { token },
          connect: true,
        }
      );

      providerRef.current = provider;

      // Handle connection status
      provider.on('status', (event: { status: string }) => {
        if (!mountedRef.current) return;

        if (event.status === 'connected') {
          setStatus('connected');
          onStatusChangeRef.current?.('connected');
        } else if (event.status === 'disconnected') {
          setStatus('disconnected');
          onStatusChangeRef.current?.('disconnected');
        }
      });

      // Handle sync - only expose yXmlFragment after sync
      provider.on('sync', (synced: boolean) => {
        if (!mountedRef.current) return;

        if (synced) {
          setYXmlFragment(pmFragment);
          setIsSynced(true);
          onSyncRef.current?.(pmFragment, doc);
        }
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
        setStatus('error');
        onStatusChangeRef.current?.('error');
      });

      // Handle connection close
      provider.on('connection-close', (event: CloseEvent | null) => {
        if (!mountedRef.current) return;
        if (event?.code === 1008) {
          setError('Authentication failed');
          setStatus('error');
          onStatusChangeRef.current?.('error');
        }
      });
    } catch (err) {
      console.error('Failed to create Yjs provider:', err);
      setError(err instanceof Error ? err.message : 'Connection failed');
      setStatus('error');
      onStatusChangeRef.current?.('error');
    }
  }, [songId, accessToken, isAuthenticated, disconnect]);

  // Reconnect
  const reconnect = useCallback(() => {
    disconnect();
    // Small delay to ensure cleanup completes
    setTimeout(() => connect(), 50);
  }, [connect, disconnect]);

  // Auto-connect on mount - only depends on stable values
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
    yXmlFragment,
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
