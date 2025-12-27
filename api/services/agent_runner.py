"""
Background agent runner service.

Runs agent tasks asynchronously and streams updates via WebSocket.
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from api.agents.workflow import (
    run_critic_workflow,
    run_orchestrator_workflow,
    TaskType,
    AgentEvent,
    AgentResult,
)
from api.enums import AgentTaskType, AgentType
from api.models import Song
from api.services.agent_review_store import AgentReviewStore
from api.jobs import job_manager
from api.jobs.models import JobType
from api.websocket import connection_manager

logger = logging.getLogger(__name__)


def _task_exception_handler(task: asyncio.Task[Any]) -> None:
    """Handle exceptions from background tasks to prevent silent failures."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error(f"Background task {task.get_name()} failed with unhandled exception: {exc}")


# Map our enums to workflow TaskType
TASK_TYPE_MAP = {
    AgentTaskType.FULL_REVIEW: TaskType.FULL_REVIEW,
    AgentTaskType.CHECK_CLICHES: TaskType.CHECK_CLICHES,
    AgentTaskType.ANALYZE_RHYTHM: TaskType.ANALYZE_RHYTHM,
    AgentTaskType.SECTION_REVIEW: TaskType.SECTION_REVIEW,
}


async def run_agent_task(
    song: Song,
    task_type: AgentTaskType,
    review_store: AgentReviewStore,
    user_id: UUID,
    llm: str | None = None,
    section_index: int | None = None,
) -> str:
    """
    Run an agent task with WebSocket streaming.

    Args:
        song: The song to analyze
        task_type: Type of analysis to perform
        review_store: Store for persisting the review
        user_id: ID of the user running the task
        llm: Optional LLM to use (e.g., "ollama/mistral")
        section_index: Section index for section reviews

    Returns:
        task_id that can be used to track progress via WebSocket
    """
    # Create the job
    job = await job_manager.create_job(JobType.AGENT_TASK, user_id)
    task_id = job.job_id

    # Run the agent task in the background with exception handling
    task = asyncio.create_task(
        _run_agent_task_async(
            task_id=task_id,
            song=song,
            task_type=task_type,
            review_store=review_store,
            llm=llm,
            section_index=section_index,
        ),
        name=f"agent_task_{task_id}",
    )
    task.add_done_callback(_task_exception_handler)

    return task_id


async def _run_agent_task_async(
    task_id: str,
    song: Song,
    task_type: AgentTaskType,
    review_store: AgentReviewStore,
    llm: str | None,
    section_index: int | None,
) -> None:
    """Run the agent task asynchronously with streaming."""
    try:
        # Create event callback that broadcasts to WebSocket
        async def on_event(event: AgentEvent):
            """Broadcast agent events to WebSocket subscribers."""
            ws_event = {
                "event": event.event_type,
                "data": {
                    "task_id": task_id,
                    **event.data,
                },
                "timestamp": event.timestamp,
            }
            await connection_manager.broadcast_to_job(task_id, ws_event)

        # Wrapper to handle async callback from sync context
        def sync_on_event(event: AgentEvent):
            asyncio.create_task(on_event(event))

        # Map task type
        workflow_task_type = TASK_TYPE_MAP.get(task_type)
        if not workflow_task_type:
            raise ValueError(f"Unknown task type: {task_type}")

        # Run the workflow
        result = await run_critic_workflow(
            song=song,
            task_type=workflow_task_type,
            section_index=section_index,
            model=llm,
            on_event=sync_on_event,
        )

        # Store the review in the database
        await review_store.create(
            song_id=song.id,
            agent_type=AgentType.CRITIC,
            task_type=task_type,
            result=result.result,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_cost_usd=result.total_cost_usd,
            duration_ms=result.duration_ms,
            model=result.model,
            success=result.success,
            error_message=result.error_message,
        )

        # Complete the job
        await job_manager.complete_job(
            task_id,
            {
                "success": result.success,
                "result": result.result,
                "duration_ms": result.duration_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_cost_usd": str(result.total_cost_usd),
            },
        )

    except Exception as e:
        logger.error(f"Agent task {task_id} failed: {e}")

        # Broadcast failure
        await connection_manager.broadcast_to_job(
            task_id,
            {
                "event": "agent.failed",
                "data": {"task_id": task_id, "error": str(e)},
            },
        )

        # Fail the job
        await job_manager.fail_job(task_id, str(e))


async def run_chat_task(
    song: Song,
    user_message: str,
    conversation_history: list[dict],
    user_id: UUID,
    llm: str | None = None,
) -> str:
    """
    Run a chat task with the orchestrator agent.

    Args:
        song: The song context
        user_message: The user's message
        conversation_history: Previous conversation turns [{role, content}]
        user_id: ID of the user running the task
        llm: Optional LLM to use

    Returns:
        task_id that can be used to track progress via WebSocket
    """
    job = await job_manager.create_job(JobType.AGENT_TASK, user_id)
    task_id = job.job_id

    # Run chat task with exception handling
    task = asyncio.create_task(
        _run_chat_task_async(
            task_id=task_id,
            song=song,
            user_message=user_message,
            conversation_history=conversation_history,
            llm=llm,
        ),
        name=f"chat_task_{task_id}",
    )
    task.add_done_callback(_task_exception_handler)

    return task_id


async def _run_chat_task_async(
    task_id: str,
    song: Song,
    user_message: str,
    conversation_history: list[dict],
    llm: str | None,
) -> None:
    """Run the chat task asynchronously with streaming."""
    try:
        async def on_event(event: AgentEvent):
            """Broadcast agent events to WebSocket subscribers."""
            ws_event = {
                "event": event.event_type,
                "data": {
                    "task_id": task_id,
                    **event.data,
                },
                "timestamp": event.timestamp,
            }
            await connection_manager.broadcast_to_job(task_id, ws_event)

        def sync_on_event(event: AgentEvent):
            asyncio.create_task(on_event(event))

        # Run the orchestrator workflow
        result = await run_orchestrator_workflow(
            song=song,
            user_message=user_message,
            conversation_history=conversation_history,
            model=llm,
            on_event=sync_on_event,
        )

        # Complete the job
        await job_manager.complete_job(
            task_id,
            {
                "success": result.success,
                "result": result.result,
                "duration_ms": result.duration_ms,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_cost_usd": str(result.total_cost_usd),
            },
        )

    except Exception as e:
        logger.error(f"Chat task {task_id} failed: {e}")

        await connection_manager.broadcast_to_job(
            task_id,
            {
                "event": "agent.failed",
                "data": {"task_id": task_id, "error": str(e)},
            },
        )

        await job_manager.fail_job(task_id, str(e))
