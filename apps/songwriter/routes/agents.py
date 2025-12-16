"""
Agent routes for AI-powered songwriting assistance.

Endpoints:
    POST /agents/{song_id}/review         - Start full song review (async)
    POST /agents/{song_id}/review-section - Start section review (async)
    POST /agents/{song_id}/check-cliches  - Start cliche scan (async)
    POST /agents/{song_id}/analyze-rhythm - Start rhythm analysis (async)
    GET  /agents/{song_id}/reviews        - Get review history for a song
    GET  /agents/tasks/{task_id}          - Get task status

All review endpoints return immediately with a task_id.
Connect to WebSocket at /ws/jobs/{task_id} for real-time progress updates.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.songwriter.enums import AgentTaskType, AgentType
from apps.songwriter.services.agent_review_store import AgentReviewStore
from apps.songwriter.services.agent_runner import run_agent_task
from apps.songwriter.services.db_store import SongDBStore
from packages.core.database import get_session_dependency
from packages.core.jobs import job_manager

# Anonymous user ID for standalone songwriter app (no auth)
ANONYMOUS_USER_ID = UUID("00000000-0000-0000-0000-000000000000")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Agents"])


# Dependencies

async def get_db_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongDBStore:
    """Get a database-backed song store."""
    return SongDBStore(session)


async def get_review_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> AgentReviewStore:
    """Get a database-backed review store."""
    return AgentReviewStore(session)


# Request/Response models

class ReviewRequest(BaseModel):
    """Request for agent review."""

    llm: Optional[str] = Field(
        None,
        description="LLM to use (e.g., 'ollama/mistral', 'gpt-4'). Uses default if not specified.",
    )


class SectionReviewRequest(BaseModel):
    """Request to review a specific section."""

    section_index: int = Field(..., ge=0, description="Index of the section to review (0-based)")
    llm: Optional[str] = None


class AgentTaskResponse(BaseModel):
    """Response when an agent task is started."""

    task_id: str = Field(..., description="Task ID to track progress via WebSocket")
    song_id: UUID
    song_title: str
    task_type: str
    message: str = Field(
        default="Task started. Connect to WebSocket for progress updates.",
        description="Status message",
    )
    websocket_url: str = Field(..., description="WebSocket URL for progress updates")


class TaskStatusResponse(BaseModel):
    """Response for task status query."""

    task_id: str
    status: str
    progress: Optional[dict] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class ReviewHistoryItem(BaseModel):
    """A single review in the history."""

    id: UUID
    agent_type: AgentType
    task_type: AgentTaskType
    result: str
    input_tokens: int
    output_tokens: int
    total_cost_usd: Decimal
    duration_ms: Optional[int]
    model: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReviewHistoryResponse(BaseModel):
    """Response for review history."""

    song_id: UUID
    reviews: list[ReviewHistoryItem]
    total_cost_usd: Decimal


# Routes

@router.post("/{song_id}/review", response_model=AgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def review_song(
    song_id: UUID,
    request: ReviewRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
):
    """
    Start a comprehensive review of a song from the Critic agent.

    Returns immediately with a task_id. Connect to the WebSocket
    at /ws/jobs/{task_id} for real-time progress updates.

    The agent will analyze:
    - Lyrical quality and originality
    - Structure and flow
    - Rhythm and meter
    - Clichés and overused phrases
    - Specific actionable improvements
    """
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    if not song.sections:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Song has no sections to review. Add some content first.",
        )

    logger.info(f"Starting full review of song '{song.title}' ({song_id})")

    task_id = await run_agent_task(
        song=song,
        task_type=AgentTaskType.FULL_REVIEW,
        review_store=review_store,
        user_id=ANONYMOUS_USER_ID,
        llm=request.llm,
    )

    return AgentTaskResponse(
        task_id=task_id,
        song_id=song_id,
        song_title=song.title,
        task_type="full_review",
        websocket_url=f"/ws/jobs/{task_id}",
    )


@router.post("/{song_id}/review-section", response_model=AgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def review_section(
    song_id: UUID,
    request: SectionReviewRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
):
    """
    Start review of a specific section of the song.

    Returns immediately with a task_id for WebSocket tracking.
    """
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    if request.section_index >= len(song.sections):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Section {request.section_index} does not exist. Song has {len(song.sections)} sections (0-{len(song.sections)-1}).",
        )

    section = song.sections[request.section_index]
    section_name = section.type.value
    if section.number:
        section_name += f" {section.number}"

    logger.info(f"Starting review of section {section_name} in '{song.title}'")

    task_id = await run_agent_task(
        song=song,
        task_type=AgentTaskType.SECTION_REVIEW,
        review_store=review_store,
        user_id=ANONYMOUS_USER_ID,
        llm=request.llm,
        section_index=request.section_index,
    )

    return AgentTaskResponse(
        task_id=task_id,
        song_id=song_id,
        song_title=song.title,
        task_type=f"section_review_{section_name}",
        websocket_url=f"/ws/jobs/{task_id}",
    )


@router.post("/{song_id}/check-cliches", response_model=AgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def check_cliches(
    song_id: UUID,
    request: ReviewRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
):
    """
    Start a scan for clichés and overused phrases.

    Returns immediately with a task_id for WebSocket tracking.
    """
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    if not song.sections:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Song has no content to check.",
        )

    logger.info(f"Starting cliche check in '{song.title}'")

    task_id = await run_agent_task(
        song=song,
        task_type=AgentTaskType.CHECK_CLICHES,
        review_store=review_store,
        user_id=ANONYMOUS_USER_ID,
        llm=request.llm,
    )

    return AgentTaskResponse(
        task_id=task_id,
        song_id=song_id,
        song_title=song.title,
        task_type="check_cliches",
        websocket_url=f"/ws/jobs/{task_id}",
    )


@router.post("/{song_id}/analyze-rhythm", response_model=AgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_rhythm(
    song_id: UUID,
    request: ReviewRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
):
    """
    Start rhythm and meter analysis of the song.

    Returns immediately with a task_id for WebSocket tracking.
    """
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    if not song.sections:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Song has no content to analyze.",
        )

    logger.info(f"Starting rhythm analysis of '{song.title}'")

    task_id = await run_agent_task(
        song=song,
        task_type=AgentTaskType.ANALYZE_RHYTHM,
        review_store=review_store,
        user_id=ANONYMOUS_USER_ID,
        llm=request.llm,
    )

    return AgentTaskResponse(
        task_id=task_id,
        song_id=song_id,
        song_title=song.title,
        task_type="analyze_rhythm",
        websocket_url=f"/ws/jobs/{task_id}",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of an agent task.

    Use this to poll for results if WebSocket is not available.
    """
    job = await job_manager.get_job(task_id)
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")

    return TaskStatusResponse(
        task_id=task_id,
        status=job.status.value,
        progress=job.progress.__dict__ if job.progress else None,
        result=job.result,
        error=job.error,
    )


@router.get("/{song_id}/reviews", response_model=ReviewHistoryResponse)
async def get_review_history(
    song_id: UUID,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
    agent_type: Optional[AgentType] = None,
    limit: int = 50,
):
    """
    Get the review history for a song.

    Optionally filter by agent type.
    """
    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    reviews = await review_store.get_by_song(song_id, agent_type=agent_type, limit=limit)
    total_cost = await review_store.get_total_cost_for_song(song_id)

    return ReviewHistoryResponse(
        song_id=song_id,
        reviews=[ReviewHistoryItem.model_validate(r) for r in reviews],
        total_cost_usd=total_cost,
    )
