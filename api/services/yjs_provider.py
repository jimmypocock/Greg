"""Yjs WebSocket provider for real-time collaborative editing.

This module provides the server-side WebSocket handling for Yjs CRDT
synchronization. It handles:
- Client connections and authentication
- Document synchronization (sync protocol)
- Broadcasting changes to all connected clients
- Persistence to the database
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from pycrdt import Doc, Array, Map, Text

from api.services.yjs_store import YjsDocumentStore

logger = logging.getLogger(__name__)

# Message types for Yjs sync protocol
MSG_SYNC = 0
MSG_AWARENESS = 1

# Sync message subtypes
MSG_SYNC_REQUEST = 0
MSG_SYNC_RESPONSE = 1
MSG_SYNC_UPDATE = 2


@dataclass
class ConnectedClient:
    """A connected WebSocket client."""

    websocket: WebSocket
    user_id: UUID
    song_id: UUID
    awareness_state: dict = field(default_factory=dict)


class YjsProvider:
    """Provider for Yjs WebSocket synchronization.

    Manages connections, synchronization, and persistence for
    collaborative Yjs documents.
    """

    def __init__(self):
        # Map of song_id -> list of connected clients
        self._connections: dict[UUID, list[ConnectedClient]] = defaultdict(list)
        # Map of song_id -> Yjs Doc
        self._documents: dict[UUID, Doc] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        song_id: UUID,
        user_id: UUID,
        store: YjsDocumentStore,
    ) -> ConnectedClient:
        """Handle a new WebSocket connection."""
        await websocket.accept()

        client = ConnectedClient(
            websocket=websocket,
            user_id=user_id,
            song_id=song_id,
        )

        async with self._lock:
            self._connections[song_id].append(client)

            # Load or create document if not in memory
            if song_id not in self._documents:
                doc = await self._load_document(song_id, store)
                self._documents[song_id] = doc

        logger.info(
            f"Client connected to song {song_id}: user={user_id}, "
            f"total_clients={len(self._connections[song_id])}"
        )

        return client

    async def disconnect(
        self,
        client: ConnectedClient,
        store: YjsDocumentStore,
    ):
        """Handle a WebSocket disconnection."""
        song_id = client.song_id

        async with self._lock:
            if song_id in self._connections:
                self._connections[song_id] = [
                    c for c in self._connections[song_id]
                    if c.websocket != client.websocket
                ]

                # If no more clients, persist and remove document
                if not self._connections[song_id]:
                    if song_id in self._documents:
                        await self._persist_document(song_id, store, client.user_id)
                        del self._documents[song_id]
                    del self._connections[song_id]

        logger.info(
            f"Client disconnected from song {song_id}: user={client.user_id}"
        )

    async def handle_message(
        self,
        client: ConnectedClient,
        message: bytes,
        store: YjsDocumentStore,
    ):
        """Handle an incoming WebSocket message."""
        if len(message) < 1:
            return

        msg_type = message[0]

        if msg_type == MSG_SYNC:
            await self._handle_sync_message(client, message[1:], store)
        elif msg_type == MSG_AWARENESS:
            await self._handle_awareness_message(client, message[1:])

    async def _handle_sync_message(
        self,
        client: ConnectedClient,
        message: bytes,
        store: YjsDocumentStore,
    ):
        """Handle Yjs sync protocol messages."""
        if len(message) < 1:
            return

        song_id = client.song_id
        msg_subtype = message[0]
        payload = message[1:]

        doc = self._documents.get(song_id)
        if doc is None:
            return

        if msg_subtype == MSG_SYNC_REQUEST:
            # Client requesting sync - send current state
            state_vector = payload
            try:
                # Get diff between client state and server state
                diff = doc.get_update(state_vector)
                # Send sync response with diff
                response = bytes([MSG_SYNC, MSG_SYNC_RESPONSE]) + diff
                await client.websocket.send_bytes(response)
            except Exception as e:
                logger.error(f"Error handling sync request: {e}")

        elif msg_subtype == MSG_SYNC_RESPONSE:
            # Received state from client - apply update
            try:
                doc.apply_update(payload)
                # Persist changes
                await self._persist_document(song_id, store, client.user_id)
            except Exception as e:
                logger.error(f"Error applying sync response: {e}")

        elif msg_subtype == MSG_SYNC_UPDATE:
            # Client sent an update - apply and broadcast
            try:
                doc.apply_update(payload)
                # Broadcast to other clients
                await self._broadcast_update(song_id, payload, exclude=client)
                # Persist changes
                await self._persist_document(song_id, store, client.user_id)
            except Exception as e:
                logger.error(f"Error handling sync update: {e}")

    async def _handle_awareness_message(
        self,
        client: ConnectedClient,
        message: bytes,
    ):
        """Handle awareness protocol messages (cursor positions, etc.)."""
        # Broadcast awareness to other clients
        song_id = client.song_id
        full_message = bytes([MSG_AWARENESS]) + message

        for other_client in self._connections.get(song_id, []):
            if other_client.websocket != client.websocket:
                try:
                    await other_client.websocket.send_bytes(full_message)
                except Exception:
                    pass  # Client may have disconnected

    async def _broadcast_update(
        self,
        song_id: UUID,
        update: bytes,
        exclude: Optional[ConnectedClient] = None,
    ):
        """Broadcast an update to all connected clients."""
        message = bytes([MSG_SYNC, MSG_SYNC_UPDATE]) + update

        for client in self._connections.get(song_id, []):
            if exclude and client.websocket == exclude.websocket:
                continue
            try:
                await client.websocket.send_bytes(message)
            except Exception:
                pass  # Client may have disconnected

    async def _load_document(
        self, song_id: UUID, store: YjsDocumentStore
    ) -> Doc:
        """Load a document from the database or create new."""
        doc = Doc()

        state_vector, document_state = await store.get_state(song_id)
        if document_state:
            try:
                doc.apply_update(document_state)
                logger.debug(f"Loaded Yjs document for song {song_id}")
            except Exception as e:
                logger.error(f"Error loading Yjs document: {e}")
                # Return fresh document if load fails
                doc = Doc()

        return doc

    async def _persist_document(
        self,
        song_id: UUID,
        store: YjsDocumentStore,
        user_id: Optional[UUID] = None,
    ):
        """Persist document state to the database."""
        doc = self._documents.get(song_id)
        if doc is None:
            return

        try:
            state_vector = doc.get_state()
            document_state = doc.get_update()

            await store.save_state(
                song_id=song_id,
                state_vector=state_vector,
                document_state=document_state,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Error persisting Yjs document: {e}")

    async def send_initial_state(
        self,
        client: ConnectedClient,
    ):
        """Send the initial document state to a newly connected client."""
        song_id = client.song_id
        doc = self._documents.get(song_id)
        if doc is None:
            return

        try:
            # Send sync step 1: our state vector
            state_vector = doc.get_state()
            message = bytes([MSG_SYNC, MSG_SYNC_REQUEST]) + state_vector
            await client.websocket.send_bytes(message)

            # Send full document state
            document_state = doc.get_update()
            response = bytes([MSG_SYNC, MSG_SYNC_RESPONSE]) + document_state
            await client.websocket.send_bytes(response)
        except Exception as e:
            logger.error(f"Error sending initial state: {e}")


# Global provider instance
yjs_provider = YjsProvider()
