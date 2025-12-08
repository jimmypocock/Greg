"""
WebSocket routes.

Provides real-time job progress updates via WebSocket connections.

Endpoints:
    WS /ws/jobs/{job_id}  - Subscribe to job progress updates
    WS /ws                - General WebSocket connection
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.jobs import job_manager
from src.websocket import (
    EventType,
    connection_manager,
    create_error_event,
    create_event,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Public functions


@router.websocket("/ws")
async def websocket_general(websocket: WebSocket):
    """
    General WebSocket endpoint for subscribing to multiple jobs.

    Clients can send messages to subscribe/unsubscribe from specific jobs.

    Client messages:
    - {"type": "subscribe", "job_id": "uuid"}
    - {"type": "unsubscribe", "job_id": "uuid"}
    - {"type": "ping"}

    Server messages:
    - {"type": "subscribed", "job_id": "uuid", "data": {"job": {...}}}
    - {"type": "unsubscribed", "job_id": "uuid"}
    - {"type": "job.progress", "job_id": "uuid", "data": {...}}
    - {"type": "job.completed", "job_id": "uuid", "data": {...}}
    - {"type": "job.failed", "job_id": "uuid", "data": {...}}
    - {"type": "error", "data": {"message": "..."}}
    - {"type": "pong"}
    """
    await connection_manager.connect(websocket)

    try:
        await websocket.send_json(create_event(EventType.CONNECTED))

        while True:
            try:
                data = await websocket.receive_json()
                message_type = data.get("type")

                if message_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif message_type == "subscribe":
                    job_id = data.get("job_id")
                    if not job_id:
                        await websocket.send_json(
                            create_error_event("job_id required for subscribe")
                        )
                        continue

                    job = await job_manager.get_job(job_id)
                    if not job:
                        await websocket.send_json(
                            create_error_event(f"Job {job_id} not found")
                        )
                        continue

                    await connection_manager.subscribe_to_job(websocket, job_id)
                    await websocket.send_json(
                        create_event(
                            EventType.SUBSCRIBED,
                            data={"job": job.to_dict()},
                            job_id=job_id,
                        )
                    )

                elif message_type == "unsubscribe":
                    job_id = data.get("job_id")
                    if job_id:
                        await connection_manager.unsubscribe_from_job(websocket, job_id)
                        await websocket.send_json(
                            create_event(EventType.UNSUBSCRIBED, job_id=job_id)
                        )

                else:
                    await websocket.send_json(
                        create_error_event(f"Unknown message type: {message_type}")
                    )

            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("General WebSocket disconnected")
    except Exception as e:
        logger.error(f"General WebSocket error: {e}")
        try:
            await websocket.send_json(create_error_event(str(e)))
        except Exception:
            pass
    finally:
        await connection_manager.disconnect(websocket)


@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_updates(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for subscribing to job progress updates.

    Clients connect to receive real-time updates about a specific job's
    progress, completion, or failure.

    Message format (sent to client):
    {
        "type": "job.progress" | "job.completed" | "job.failed",
        "job_id": "uuid",
        "data": { ... }
    }
    """
    job = await job_manager.get_job(job_id)
    if not job:
        await websocket.close(code=4004, reason="Job not found")
        return

    await connection_manager.connect(websocket, job_id=job_id)

    try:
        await websocket.send_json(
            create_event(
                EventType.SUBSCRIBED,
                data={"job": job.to_dict()},
                job_id=job_id,
            )
        )

        if job.status.value in ("completed", "failed", "cancelled"):
            await websocket.close(code=1000, reason="Job already finished")
            return

        while True:
            try:
                data = await websocket.receive_json()

                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})

            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        try:
            await websocket.send_json(create_error_event(str(e)))
        except Exception:
            pass
    finally:
        await connection_manager.disconnect(websocket)
