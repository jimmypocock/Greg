'use client';

/**
 * Yjs Song Hook
 *
 * Manages a Yjs WebSocket connection for real-time collaborative editing
 * of a song document. Provides connection status and the Yjs document.
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

export interface YjsSongState {
  /** The Yjs document */
  doc: Y.Doc | null;
  /** WebSocket provider */
  provider: WebsocketProvider | null;
  /** Connection status */
  status: ConnectionStatus;
  /** Error message if status is 'error' */
  error: string | null;
  /** Number of connected users (including self) */
  connectedUsers: number;
  /** Reconnect manually */
  reconnect: () => void;
  /** Disconnect manually */
  disconnect: () => void;
}

export interface UseYjsSongOptions {
  /** Song ID to connect to */
  songId: string;
  /** Whether to auto-connect (default: true) */
  autoConnect?: boolean;
  /** Callback when document syncs */
  onSync?: (doc: Y.Doc) => void;
  /** Callback when connection status changes */
  onStatusChange?: (status: ConnectionStatus) => void;
}

/**
 * Hook for managing a Yjs WebSocket connection to a song document.
 *
 * @example
 * ```tsx
 * const { doc, status, connectedUsers } = useYjsSong({
 *   songId: song.id,
 *   onSync: (doc) => console.log('Document synced'),
 * });
 *
 * if (status === 'connected' && doc) {
 *   const meta = doc.getMap('meta');
 *   const sections = doc.getArray('sections');
 * }
 * ```
 */
export function useYjsSong({
  songId,
  autoConnect = true,
  onSync,
  onStatusChange,
}: UseYjsSongOptions): YjsSongState {
  const { accessToken, isAuthenticated } = useAuth();
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const [connectedUsers, setConnectedUsers] = useState(0);

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

    // Create new Yjs document
    const doc = new Y.Doc();
    docRef.current = doc;

    // Build WebSocket URL with token
    const wsUrl = getWebSocketUrl();
    // y-websocket appends roomName to serverUrl, so we structure it as:
    // serverUrl = ws://host/ws/songs
    // roomName = {songId}/yjs
    // Result: ws://host/ws/songs/{songId}/yjs
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

        if (event.status === 'connected') {
          updateStatus('connected');
        } else if (event.status === 'disconnected') {
          updateStatus('disconnected');
        }
      });

      // Handle sync
      provider.on('sync', (synced: boolean) => {
        if (!mountedRef.current) return;

        if (synced) {
          onSync?.(doc);
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
        updateStatus('error');
      });

      // Handle connection close
      provider.on('connection-close', (event: CloseEvent | null) => {
        if (!mountedRef.current) return;

        if (event?.code === 1008) {
          // Policy violation - likely auth failure
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
    doc: docRef.current,
    provider: providerRef.current,
    status,
    error,
    connectedUsers,
    reconnect,
    disconnect,
  };
}
