"""
WebSocket connection manager.

Handles WebSocket connections, message broadcasting, and connection lifecycle.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Supports both global broadcasts and targeted messages to specific
    connections or groups (e.g., job subscribers).
    """

    def __init__(self):
        # All active connections
        self._connections: set[WebSocket] = set()
        # Connections grouped by job_id for targeted broadcasts
        self._job_connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, job_id: str | None = None) -> None:
        """
        Accept a WebSocket connection and optionally subscribe to a job.

        Args:
            websocket: The WebSocket connection to accept.
            job_id: Optional job ID to subscribe to for updates.
        """
        await websocket.accept()

        async with self._lock:
            self._connections.add(websocket)

            if job_id:
                if job_id not in self._job_connections:
                    self._job_connections[job_id] = set()
                self._job_connections[job_id].add(websocket)

        logger.info(f"WebSocket connected (job_id={job_id})")

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a WebSocket connection from all tracking.

        Args:
            websocket: The WebSocket connection to remove.
        """
        async with self._lock:
            self._connections.discard(websocket)

            # Remove from all job subscriptions
            for job_id in list(self._job_connections.keys()):
                self._job_connections[job_id].discard(websocket)
                if not self._job_connections[job_id]:
                    del self._job_connections[job_id]

        logger.info("WebSocket disconnected")

    async def subscribe_to_job(self, websocket: WebSocket, job_id: str) -> None:
        """
        Subscribe a connection to a specific job's updates.

        Args:
            websocket: The WebSocket connection.
            job_id: The job ID to subscribe to.
        """
        async with self._lock:
            if job_id not in self._job_connections:
                self._job_connections[job_id] = set()
            self._job_connections[job_id].add(websocket)

        logger.debug(f"WebSocket subscribed to job {job_id}")

    async def unsubscribe_from_job(self, websocket: WebSocket, job_id: str) -> None:
        """
        Unsubscribe a connection from a job's updates.

        Args:
            websocket: The WebSocket connection.
            job_id: The job ID to unsubscribe from.
        """
        async with self._lock:
            if job_id in self._job_connections:
                self._job_connections[job_id].discard(websocket)
                if not self._job_connections[job_id]:
                    del self._job_connections[job_id]

    async def send_to_connection(
        self, websocket: WebSocket, message: dict[str, Any]
    ) -> bool:
        """
        Send a message to a specific WebSocket connection.

        Args:
            websocket: The target WebSocket.
            message: The message to send (will be JSON serialized).

        Returns:
            True if sent successfully, False otherwise.
        """
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            return False

    async def broadcast_to_job(self, job_id: str, message: dict[str, Any]) -> int:
        """
        Broadcast a message to all connections subscribed to a job.

        Args:
            job_id: The job ID to broadcast to.
            message: The message to send.

        Returns:
            Number of connections that received the message.
        """
        async with self._lock:
            connections = self._job_connections.get(job_id, set()).copy()

        if not connections:
            return 0

        sent_count = 0
        failed_connections = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to WebSocket: {e}")
                failed_connections.append(websocket)

        # Clean up failed connections
        if failed_connections:
            async with self._lock:
                for ws in failed_connections:
                    self._connections.discard(ws)
                    if job_id in self._job_connections:
                        self._job_connections[job_id].discard(ws)

        return sent_count

    async def broadcast_all(self, message: dict[str, Any]) -> int:
        """
        Broadcast a message to all connected WebSockets.

        Args:
            message: The message to send.

        Returns:
            Number of connections that received the message.
        """
        async with self._lock:
            connections = self._connections.copy()

        sent_count = 0
        failed_connections = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
                sent_count += 1
            except Exception:
                failed_connections.append(websocket)

        # Clean up failed connections
        if failed_connections:
            async with self._lock:
                for ws in failed_connections:
                    self._connections.discard(ws)

        return sent_count

    @property
    def connection_count(self) -> int:
        """Get the total number of active connections."""
        return len(self._connections)

    def get_job_subscriber_count(self, job_id: str) -> int:
        """Get the number of subscribers for a specific job."""
        return len(self._job_connections.get(job_id, set()))


# Global connection manager instance
connection_manager = ConnectionManager()
