"""Yjs WebSocket provider for real-time collaborative editing.

This module provides the server-side WebSocket handling for Yjs CRDT
synchronization with Redis pub/sub for multi-server support.

Features:
- Client connections and authentication
- Document synchronization (sync protocol)
- Redis pub/sub for cross-server broadcasting
- Debounced persistence to the database
- In-memory document cache with eviction
"""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import WebSocket

from api.services.yjs_store import YjsDocumentStore

# Import pycrdt - handle potential import issues
try:
    from pycrdt import Doc, Text
except ImportError:
    Doc = None
    Text = None
    logging.warning("pycrdt not available - Yjs features disabled")

logger = logging.getLogger(__name__)

# Message types for Yjs sync protocol
MSG_SYNC = 0
MSG_AWARENESS = 1

# Sync message subtypes
MSG_SYNC_REQUEST = 0
MSG_SYNC_RESPONSE = 1
MSG_SYNC_UPDATE = 2


def write_var_uint(value: int) -> bytes:
    """Encode an unsigned integer using variable-length encoding (y-protocols format)."""
    result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result) if result else bytes([0])


def read_var_uint(data: bytes, offset: int = 0) -> tuple[int, int]:
    """Decode a variable-length unsigned integer. Returns (value, new_offset)."""
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        value |= (byte & 0x7F) << shift
        offset += 1
        if (byte & 0x80) == 0:
            break
        shift += 7
    return value, offset


def write_var_byte_array(data: bytes) -> bytes:
    """Encode a byte array with length prefix (y-protocols format)."""
    return write_var_uint(len(data)) + data


def read_var_byte_array(data: bytes, offset: int = 0) -> tuple[bytes, int]:
    """Decode a length-prefixed byte array. Returns (bytes, new_offset)."""
    length, offset = read_var_uint(data, offset)
    return data[offset:offset + length], offset + length


@dataclass
class ConnectedClient:
    """A connected WebSocket client."""

    websocket: WebSocket
    user_id: UUID
    song_id: UUID
    awareness_state: dict = field(default_factory=dict)


class YjsProvider:
    """
    Provider for Yjs WebSocket synchronization with Redis pub/sub.

    Manages connections, synchronization, and persistence for
    collaborative Yjs documents across multiple server instances.
    """

    # Configuration
    MAX_DOCS_IN_MEMORY = 500
    MAX_CLIENTS_PER_DOC = 50
    PERSIST_DEBOUNCE_SECONDS = 2.0
    DOC_IDLE_TIMEOUT_SECONDS = 300  # 5 minutes

    def __init__(self):
        # Map of song_id -> list of connected clients
        self._connections: dict[UUID, list[ConnectedClient]] = defaultdict(list)
        # Map of song_id -> Yjs Doc
        self._documents: dict[UUID, Doc] = {}
        # Map of song_id -> last access timestamp
        self._doc_last_access: dict[UUID, float] = {}
        # Map of song_id -> pending persist task
        self._persist_tasks: dict[UUID, asyncio.Task] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        # Redis
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._pubsub_task: Optional[asyncio.Task] = None
        self._subscribed_songs: set[UUID] = set()

        # Initialization state
        self._initialized = False

    async def initialize(self, redis_url: str) -> None:
        """
        Initialize Redis connection and start pub/sub listener.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379)
        """
        if self._initialized:
            return

        try:
            self._redis = await aioredis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=False,  # We need bytes for Yjs
            )
            # Test connection
            await self._redis.ping()

            # Start pub/sub listener
            self._pubsub = self._redis.pubsub()
            self._pubsub_task = asyncio.create_task(self._pubsub_listener())

            self._initialized = True
            logger.info("YjsProvider initialized with Redis")

        except Exception as e:
            logger.error(f"Failed to initialize YjsProvider with Redis: {e}")
            # Continue without Redis - local-only mode
            self._redis = None
            self._initialized = True

    async def shutdown(self) -> None:
        """Clean shutdown of Redis connections."""
        # Cancel pub/sub listener
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        # Close pub/sub
        if self._pubsub:
            await self._pubsub.close()

        # Close Redis connection
        if self._redis:
            await self._redis.close()

        # Cancel pending persist tasks
        for task in self._persist_tasks.values():
            task.cancel()

        logger.info("YjsProvider shutdown complete")

    # ─────────────────────────────────────────────────────────────
    # CONNECTION MANAGEMENT
    # ─────────────────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        song_id: UUID,
        user_id: UUID,
        store: YjsDocumentStore,
    ) -> Optional[ConnectedClient]:
        """
        Handle a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            song_id: Song being edited
            user_id: User connecting
            store: Yjs document store for persistence

        Returns:
            ConnectedClient or None if connection rejected
        """
        # Check connection limit
        if len(self._connections[song_id]) >= self.MAX_CLIENTS_PER_DOC:
            logger.warning(f"Connection limit reached for song {song_id}")
            await websocket.close(code=1013, reason="Too many editors")
            return None

        await websocket.accept()

        client = ConnectedClient(
            websocket=websocket,
            user_id=user_id,
            song_id=song_id,
        )

        async with self._lock:
            self._connections[song_id].append(client)

            # Load document if not in memory, or reload if current one has empty canvas
            doc = self._documents.get(song_id)
            if doc is None:
                doc = await self._load_document(song_id, store)
                self._documents[song_id] = doc
            else:
                # Check if cached doc has empty canvas - if so, reload from DB
                # (may have been reinitialized by sync_service)
                canvas = doc.get("canvas", type=Text) if Text else None
                canvas_len = len(str(canvas)) if canvas else 0
                if canvas_len == 0:
                    print(f"[YJS] Reloading doc for {song_id} - in-memory canvas is empty")
                    doc = await self._load_document(song_id, store)
                    self._documents[song_id] = doc
                else:
                    print(f"[YJS] Using cached doc for {song_id}, canvas: {canvas_len} chars")

            # Update access time
            self._doc_last_access[song_id] = asyncio.get_event_loop().time()

            # Subscribe to Redis channel for this song
            await self._subscribe_to_song(song_id)

            # Track client in Redis (for monitoring)
            if self._redis:
                try:
                    await self._redis.sadd(f"yjs:clients:{song_id}", str(user_id))
                except Exception as e:
                    logger.warning(f"Failed to track client in Redis: {e}")

        logger.info(
            f"Client connected to song {song_id}: user={user_id}, "
            f"total_clients={len(self._connections[song_id])}"
        )

        return client

    async def disconnect(
        self,
        client: ConnectedClient,
        store: YjsDocumentStore,
    ) -> None:
        """Handle a WebSocket disconnection."""
        song_id = client.song_id

        async with self._lock:
            # Remove client from connections
            if song_id in self._connections:
                self._connections[song_id] = [
                    c for c in self._connections[song_id]
                    if c.websocket != client.websocket
                ]

                # Update Redis client tracking
                if self._redis:
                    try:
                        await self._redis.srem(f"yjs:clients:{song_id}", str(client.user_id))
                    except Exception:
                        pass

                # If no more clients for this song
                if not self._connections[song_id]:
                    # Persist document before cleanup
                    if song_id in self._documents:
                        await self._persist_document_now(song_id, store, client.user_id)

                    # Unsubscribe from Redis
                    await self._unsubscribe_from_song(song_id)

                    # Clean up (keep doc in memory briefly for reconnects)
                    del self._connections[song_id]

        logger.info(f"Client disconnected from song {song_id}: user={client.user_id}")

    # ─────────────────────────────────────────────────────────────
    # MESSAGE HANDLING
    # ─────────────────────────────────────────────────────────────

    async def handle_message(
        self,
        client: ConnectedClient,
        message: bytes,
        store: YjsDocumentStore,
    ) -> None:
        """Handle an incoming WebSocket message."""
        if len(message) < 1:
            logger.warning(f"[YJS] Received empty message from client")
            return

        # Decode message type using varUint
        msg_type, offset = read_var_uint(message, 0)
        song_id = client.song_id

        print(f"[YJS] Received message: type={msg_type}, size={len(message)} bytes, song={song_id}")

        # Update last access time
        self._doc_last_access[song_id] = asyncio.get_event_loop().time()

        if msg_type == MSG_SYNC:
            await self._handle_sync_message(client, message[offset:], store)
        elif msg_type == MSG_AWARENESS:
            await self._handle_awareness_message(client, message[offset:])
        else:
            logger.warning(f"[YJS] Unknown message type: {msg_type}")

    async def _handle_sync_message(
        self,
        client: ConnectedClient,
        message: bytes,
        store: YjsDocumentStore,
    ) -> None:
        """Handle Yjs sync protocol messages."""
        if len(message) < 1:
            return

        song_id = client.song_id

        # Decode message subtype using varUint
        msg_subtype, offset = read_var_uint(message, 0)

        # Decode the payload (varByteArray)
        payload, _ = read_var_byte_array(message, offset)

        doc = self._documents.get(song_id)
        if doc is None:
            return

        if msg_subtype == MSG_SYNC_REQUEST:
            # Client requesting sync - they sent their state vector
            # We respond with updates they're missing
            try:
                # The payload is the client's state vector
                client_state_vector = payload
                print(f"[YJS] Sync request from client with state vector of {len(client_state_vector)} bytes")

                # Get updates the client is missing based on their state vector
                # For pycrdt: get_update(state_vector) returns updates since that state
                if client_state_vector and len(client_state_vector) > 0:
                    try:
                        missing_updates = doc.get_update(client_state_vector)
                    except Exception as e:
                        logger.warning(f"[YJS] Could not compute diff, sending full state: {e}")
                        missing_updates = doc.get_update()
                else:
                    # No state vector means client is new - send everything
                    missing_updates = doc.get_update()

                canvas = doc.get("canvas", type=Text) if Text else None
                canvas_len = len(str(canvas)) if canvas else 0
                print(f"[YJS] Sending sync response: {len(missing_updates)} bytes, canvas: {canvas_len} chars")

                response = (
                    write_var_uint(MSG_SYNC) +
                    write_var_uint(MSG_SYNC_RESPONSE) +
                    write_var_byte_array(missing_updates)
                )
                await client.websocket.send_bytes(response)

                # Also send our state vector so client can send us any updates we're missing
                our_state_vector = doc.get_state()
                request = (
                    write_var_uint(MSG_SYNC) +
                    write_var_uint(MSG_SYNC_REQUEST) +
                    write_var_byte_array(our_state_vector)
                )
                await client.websocket.send_bytes(request)
                print(f"[YJS] Sent our state vector ({len(our_state_vector)} bytes) to client")

            except Exception as e:
                logger.error(f"Error handling sync request: {e}", exc_info=True)

        elif msg_subtype == MSG_SYNC_RESPONSE:
            # Received state from client - apply update
            try:
                doc.apply_update(payload)
                canvas = doc.get("canvas", type=Text) if Text else None
                canvas_len = len(str(canvas)) if canvas else 0
                print(f"[YJS] Sync response from client, applied {len(payload)} bytes, canvas now: {canvas_len} chars")
                self._schedule_persist(song_id, store, client.user_id)
            except Exception as e:
                print(f"[YJS] Error applying sync response: {e}")

        elif msg_subtype == MSG_SYNC_UPDATE:
            # Client sent an update - apply and broadcast
            try:
                # Log before apply
                canvas_before = doc.get("canvas", type=Text) if Text else None
                canvas_len_before = len(str(canvas_before)) if canvas_before else 0

                doc.apply_update(payload)

                # Check canvas after update
                canvas = doc.get("canvas", type=Text) if Text else None
                canvas_len = len(str(canvas)) if canvas else 0
                canvas_preview = str(canvas)[:100] if canvas else ""
                print(f"[YJS] Applied sync update: canvas {canvas_len_before} -> {canvas_len} chars, payload: {len(payload)} bytes")

                # Broadcast to local clients (re-encode the message properly)
                broadcast_msg = (
                    write_var_uint(MSG_SYNC) +
                    write_var_uint(MSG_SYNC_UPDATE) +
                    write_var_byte_array(payload)
                )
                await self._broadcast_local(song_id, broadcast_msg, exclude=client)

                # Publish to Redis for other servers
                await self._publish_update(song_id, broadcast_msg)

                # Schedule debounced persist
                self._schedule_persist(song_id, store, client.user_id)
                logger.debug(f"[YJS] Scheduled persist for song {song_id}")

            except Exception as e:
                logger.error(f"Error handling sync update: {e}", exc_info=True)

    async def _handle_awareness_message(
        self,
        client: ConnectedClient,
        message: bytes,
    ) -> None:
        """Handle awareness protocol messages (cursor positions, etc.)."""
        song_id = client.song_id

        # Re-encode with proper varUint format
        full_message = write_var_uint(MSG_AWARENESS) + message

        # Broadcast to local clients
        await self._broadcast_local(song_id, full_message, exclude=client)

        # Publish to Redis (send the full properly encoded message)
        await self._publish_awareness(song_id, full_message)

    # ─────────────────────────────────────────────────────────────
    # REDIS PUB/SUB
    # ─────────────────────────────────────────────────────────────

    async def _subscribe_to_song(self, song_id: UUID) -> None:
        """Subscribe to Redis channels for a song."""
        if not self._redis or not self._pubsub:
            return

        if song_id in self._subscribed_songs:
            return

        try:
            await self._pubsub.subscribe(
                f"yjs:updates:{song_id}",
                f"yjs:awareness:{song_id}",
            )
            self._subscribed_songs.add(song_id)
            logger.debug(f"Subscribed to Redis channels for song {song_id}")
        except Exception as e:
            logger.error(f"Failed to subscribe to Redis: {e}")

    async def _unsubscribe_from_song(self, song_id: UUID) -> None:
        """Unsubscribe from Redis channels for a song."""
        if not self._redis or not self._pubsub:
            return

        if song_id not in self._subscribed_songs:
            return

        try:
            await self._pubsub.unsubscribe(
                f"yjs:updates:{song_id}",
                f"yjs:awareness:{song_id}",
            )
            self._subscribed_songs.discard(song_id)
            logger.debug(f"Unsubscribed from Redis channels for song {song_id}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe from Redis: {e}")

    async def _publish_update(self, song_id: UUID, update: bytes) -> None:
        """Publish a sync update to Redis."""
        if not self._redis:
            return

        try:
            await self._redis.publish(f"yjs:updates:{song_id}", update)
        except Exception as e:
            logger.error(f"Failed to publish update to Redis: {e}")

    async def _publish_awareness(self, song_id: UUID, message: bytes) -> None:
        """Publish an awareness message to Redis."""
        if not self._redis:
            return

        try:
            await self._redis.publish(f"yjs:awareness:{song_id}", message)
        except Exception as e:
            logger.error(f"Failed to publish awareness to Redis: {e}")

    async def _pubsub_listener(self) -> None:
        """Background task that listens to Redis pub/sub messages."""
        if not self._pubsub:
            return

        logger.info("Starting Redis pub/sub listener")

        while True:
            try:
                # Skip if no subscriptions yet
                if not self._subscribed_songs:
                    await asyncio.sleep(0.5)
                    continue

                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )

                if message is None:
                    continue

                if message["type"] != "message":
                    continue

                channel = message["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode("utf-8")

                data = message["data"]
                if isinstance(data, str):
                    data = data.encode("utf-8")

                # Parse channel: yjs:{type}:{song_id}
                parts = channel.split(":")
                if len(parts) != 3:
                    continue

                _, msg_type, song_id_str = parts

                try:
                    song_id = UUID(song_id_str)
                except ValueError:
                    continue

                # Only process if we have local clients for this song
                if song_id not in self._connections:
                    continue

                # Broadcast to local clients
                if msg_type == "updates":
                    # Data is already the properly encoded sync message
                    await self._broadcast_local(song_id, data, exclude=None)

                    # Also apply to local doc - need to decode the update
                    doc = self._documents.get(song_id)
                    if doc and len(data) > 1:
                        try:
                            # Decode: varUint(MSG_SYNC) + varUint(MSG_SYNC_UPDATE) + varByteArray(payload)
                            _, offset = read_var_uint(data, 0)  # MSG_SYNC
                            msg_subtype, offset = read_var_uint(data, offset)
                            if msg_subtype == MSG_SYNC_UPDATE:
                                payload, _ = read_var_byte_array(data, offset)
                                doc.apply_update(payload)
                        except Exception as e:
                            logger.error(f"Failed to apply remote update: {e}")

                elif msg_type == "awareness":
                    # Data is already the properly encoded awareness message
                    await self._broadcast_local(song_id, data, exclude=None)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pub/sub listener error: {e}")
                await asyncio.sleep(1)

        logger.info("Redis pub/sub listener stopped")

    # ─────────────────────────────────────────────────────────────
    # BROADCASTING
    # ─────────────────────────────────────────────────────────────

    async def _broadcast_local(
        self,
        song_id: UUID,
        message: bytes,
        exclude: Optional[ConnectedClient] = None,
    ) -> None:
        """Broadcast message to local clients only."""
        for client in self._connections.get(song_id, []):
            if exclude and client.websocket == exclude.websocket:
                continue
            try:
                await client.websocket.send_bytes(message)
            except Exception:
                pass  # Client may have disconnected

    # ─────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────

    def _schedule_persist(
        self,
        song_id: UUID,
        store: YjsDocumentStore,
        user_id: UUID,
    ) -> None:
        """Schedule debounced persistence."""
        # Cancel existing task
        if song_id in self._persist_tasks:
            self._persist_tasks[song_id].cancel()

        async def do_persist():
            await asyncio.sleep(self.PERSIST_DEBOUNCE_SECONDS)
            await self._persist_document_now(song_id, store, user_id)
            self._persist_tasks.pop(song_id, None)

        self._persist_tasks[song_id] = asyncio.create_task(do_persist())

    async def _persist_document_now(
        self,
        song_id: UUID,
        store: YjsDocumentStore,
        user_id: Optional[UUID] = None,
    ) -> None:
        """Persist document to database immediately."""
        doc = self._documents.get(song_id)
        if doc is None:
            logger.warning(f"Cannot persist song {song_id}: doc not in memory")
            return

        try:
            # Check canvas content before persisting
            canvas = doc.get("canvas", type=Text) if Text else None
            canvas_len = len(str(canvas)) if canvas else 0
            print(f"[YJS] Persisting song {song_id}, canvas length: {canvas_len}")

            state_vector = doc.get_state()
            document_state = doc.get_update()

            await store.save_state(
                song_id=song_id,
                state_vector=state_vector,
                document_state=document_state,
                user_id=user_id,
            )

            logger.info(f"Persisted Yjs doc for song {song_id}: {len(document_state)} bytes")
        except Exception as e:
            logger.error(f"Failed to persist song {song_id}: {e}")

    async def _load_document(
        self,
        song_id: UUID,
        store: YjsDocumentStore,
    ) -> Doc:
        """Load document from database or create new."""
        doc = Doc()

        state_vector, document_state = await store.get_state(song_id)
        if document_state:
            try:
                doc.apply_update(document_state)
                # Check canvas content after loading - use doc.get() for proper access
                canvas = doc.get("canvas", type=Text) if Text else None
                canvas_len = len(str(canvas)) if canvas else 0
                canvas_preview = str(canvas)[:50] if canvas else ""
                print(f"[YJS] Provider loaded doc for {song_id}, canvas: {canvas_len} chars, state: {len(document_state)} bytes")
                print(f"[YJS] Canvas preview: {canvas_preview!r}")
            except Exception as e:
                print(f"[YJS] Error loading Yjs doc: {e}")
                doc = Doc()
        else:
            print(f"[YJS] No document state found for song {song_id} in store")

        return doc

    # ─────────────────────────────────────────────────────────────
    # INITIAL STATE
    # ─────────────────────────────────────────────────────────────

    async def send_initial_state(self, client: ConnectedClient) -> None:
        """Send the initial document state to a newly connected client.

        Note: We DON'T send anything here anymore. Instead, we wait for the
        client to initiate the sync protocol by sending MSG_SYNC_REQUEST.
        The y-websocket library expects to initiate the handshake.
        """
        song_id = client.song_id
        doc = self._documents.get(song_id)
        if doc is None:
            print(f"[YJS] No document found for song {song_id} when preparing initial state")
            return

        canvas = doc.get("canvas", type=Text) if Text else None
        canvas_len = len(str(canvas)) if canvas else 0
        print(f"[YJS] Client connected, waiting for sync request. Song={song_id}, canvas={canvas_len} chars")

    # ─────────────────────────────────────────────────────────────
    # UTILITIES
    # ─────────────────────────────────────────────────────────────

    def get_active_song_ids(self) -> list[UUID]:
        """Get list of songs with active documents in memory."""
        return list(self._documents.keys())

    def get_connection_count(self, song_id: UUID) -> int:
        """Get number of connected clients for a song."""
        return len(self._connections.get(song_id, []))


# Global provider instance
yjs_provider = YjsProvider()
