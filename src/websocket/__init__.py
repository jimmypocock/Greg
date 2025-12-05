"""
WebSocket infrastructure.

Provides real-time communication for job progress updates
and other live events.
"""

from src.websocket.events import (
    EventType,
    create_error_event,
    create_event,
    create_job_completed_event,
    create_job_failed_event,
    create_job_progress_event,
)
from src.websocket.manager import ConnectionManager, connection_manager

__all__ = [
    "ConnectionManager",
    "connection_manager",
    "EventType",
    "create_event",
    "create_error_event",
    "create_job_completed_event",
    "create_job_failed_event",
    "create_job_progress_event",
]
