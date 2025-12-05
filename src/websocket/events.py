"""
WebSocket event definitions.

Standardized event types for WebSocket communication.
"""

from enum import Enum
from typing import Any


class EventType(str, Enum):
    """Types of WebSocket events."""

    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    # Job events
    JOB_CREATED = "job.created"
    JOB_PROGRESS = "job.progress"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_CANCELLED = "job.cancelled"

    # Subscription events
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"


def create_event(
    event_type: EventType,
    data: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """
    Create a standardized WebSocket event message.

    Args:
        event_type: The type of event.
        data: Event payload data.
        job_id: Associated job ID, if applicable.

    Returns:
        Formatted event dictionary.
    """
    event = {
        "type": event_type.value,
        "data": data or {},
    }

    if job_id:
        event["job_id"] = job_id

    return event


def create_job_progress_event(
    job_id: str,
    stage: str,
    percent: float,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a job progress event.

    Args:
        job_id: The job ID.
        stage: Current processing stage.
        percent: Completion percentage (0-100).
        message: Human-readable status message.
        details: Additional progress details.

    Returns:
        Formatted progress event.
    """
    return create_event(
        EventType.JOB_PROGRESS,
        data={
            "stage": stage,
            "percent": percent,
            "message": message,
            "details": details or {},
        },
        job_id=job_id,
    )


def create_job_completed_event(
    job_id: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Create a job completed event.

    Args:
        job_id: The job ID.
        result: The job's result data.

    Returns:
        Formatted completion event.
    """
    return create_event(
        EventType.JOB_COMPLETED,
        data={"result": result},
        job_id=job_id,
    )


def create_job_failed_event(
    job_id: str,
    error: str,
) -> dict[str, Any]:
    """
    Create a job failed event.

    Args:
        job_id: The job ID.
        error: Error description.

    Returns:
        Formatted failure event.
    """
    return create_event(
        EventType.JOB_FAILED,
        data={"error": error},
        job_id=job_id,
    )


def create_error_event(
    message: str,
    code: str | None = None,
) -> dict[str, Any]:
    """
    Create an error event.

    Args:
        message: Error message.
        code: Optional error code.

    Returns:
        Formatted error event.
    """
    data = {"message": message}
    if code:
        data["code"] = code

    return create_event(EventType.ERROR, data=data)
