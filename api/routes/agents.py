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
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.constants import (
    MAX_CHAT_MESSAGE_LENGTH,
    MAX_CONVERSATION_HISTORY,
)
from api.dependencies import PermissionService
from api.enums import AgentTaskType, AgentType, NoteType
from api.services.agent_review_store import AgentReviewStore
from api.services.agent_runner import run_agent_task, run_chat_task, run_shaper_task
from api.services.chat_history_store import ChatHistoryStore
from api.services.db_store import SongDBStore
from api.services.permissions import Permission
from api.auth import CurrentUser
from api.billing import RequireAICredits
from api.database import get_session, get_session_dependency
from api.jobs import job_manager

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


async def get_chat_history_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> ChatHistoryStore:
    """Get a database-backed chat history store."""
    return ChatHistoryStore(session)


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


class ChatMessageRequest(BaseModel):
    """A message in the conversation history."""

    role: str = Field(..., pattern="^(user|assistant)$", description="Role: 'user' or 'assistant'")
    content: str = Field(..., min_length=1, description="Message content")


class ChatRequest(BaseModel):
    """Request for conversational chat with the AI assistant."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CHAT_MESSAGE_LENGTH,
        description="The user's message",
    )
    conversation_history: list[ChatMessageRequest] = Field(
        default_factory=list,
        max_length=MAX_CONVERSATION_HISTORY,
        description=f"Previous conversation turns (limited to last {MAX_CONVERSATION_HISTORY} messages)",
    )
    llm: Optional[str] = Field(
        None,
        description="LLM to use (e.g., 'ollama/mistral'). Uses default if not specified.",
    )


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
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
    _credits: Annotated[None, Depends(RequireAICredits())],
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
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

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
        user_id=user.id,
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
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
    _credits: Annotated[None, Depends(RequireAICredits())],
):
    """
    Start review of a specific section of the song.

    Returns immediately with a task_id for WebSocket tracking.
    """
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

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
        user_id=user.id,
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
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
    _credits: Annotated[None, Depends(RequireAICredits())],
):
    """
    Start a scan for clichés and overused phrases.

    Returns immediately with a task_id for WebSocket tracking.
    """
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

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
        user_id=user.id,
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
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
    _credits: Annotated[None, Depends(RequireAICredits())],
):
    """
    Start rhythm and meter analysis of the song.

    Returns immediately with a task_id for WebSocket tracking.
    """
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

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
        user_id=user.id,
        llm=request.llm,
    )

    return AgentTaskResponse(
        task_id=task_id,
        song_id=song_id,
        song_title=song.title,
        task_type="analyze_rhythm",
        websocket_url=f"/ws/jobs/{task_id}",
    )


@router.post("/{song_id}/chat", response_model=AgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def chat_with_song(
    song_id: UUID,
    request: ChatRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    chat_store: Annotated[ChatHistoryStore, Depends(get_chat_history_store)],
    _credits: Annotated[None, Depends(RequireAICredits())],
):
    """
    Start a conversational chat session about the song.

    The unified orchestrator adapts its behavior based on context:
    - Exploration: For new songs, asks questions and builds understanding
    - Writing: Creates sections, drafts lyrics
    - Refinement: Gives feedback, improves existing content

    The orchestrator can modify the song in real-time:
    - Create/restructure sections
    - Write/update lyrics
    - Set theme, emotional arc, key images

    Returns immediately with a task_id. Connect to the WebSocket
    at /ws/jobs/{task_id} for real-time streaming responses.

    **Chat history is persisted** - the conversation will survive errors and refreshes.

    Special events:
    - `song.updated`: Emitted when the agent creates/updates song data
    """
    # Check permission - need WRITE for song modification
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    logger.info(f"Starting chat for song '{song.title}' ({song_id})")

    # Save user message to database
    await chat_store.add_message(song_id=song_id, role="user", content=request.message)

    # Load conversation history from database (not from request)
    conversation_history = await chat_store.get_history_for_context(song_id, limit=MAX_CONVERSATION_HISTORY)

    task_id = await run_chat_task(
        song=song,
        user_message=request.message,
        conversation_history=conversation_history,
        session_factory=get_session,
        user_id=user.id,
        llm=request.llm,
        song_id=song_id,  # Pass for saving assistant response
    )

    return AgentTaskResponse(
        task_id=task_id,
        song_id=song_id,
        song_title=song.title,
        task_type="chat",
        message="Chat started. Connect to WebSocket for streaming response.",
        websocket_url=f"/ws/jobs/{task_id}",
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    user: CurrentUser,
):
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
        progress=asdict(job.progress) if job.progress else None,
        result=job.result,
        error=job.error,
    )


@router.get("/{song_id}/reviews", response_model=ReviewHistoryResponse)
async def get_review_history(
    song_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
    agent_type: Optional[AgentType] = None,
    limit: int = 50,
):
    """
    Get the review history for a song.

    Optionally filter by agent type.
    """
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

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


# =============================================================================
# Chat History Endpoints
# =============================================================================


class ChatHistoryMessage(BaseModel):
    """A message in chat history."""

    id: UUID
    role: str
    content: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_cost_usd: Optional[Decimal] = None
    duration_ms: Optional[int] = None
    model: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    """Response for chat history."""

    song_id: UUID
    messages: list[ChatHistoryMessage]


@router.get("/{song_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    song_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    chat_store: Annotated[ChatHistoryStore, Depends(get_chat_history_store)],
    limit: int = 100,
):
    """
    Get the chat history for a song.

    Returns all messages in chronological order.
    """
    await permission_service.require_permission(song_id, user.id, Permission.READ)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    messages = await chat_store.get_history(song_id, limit=limit)

    return ChatHistoryResponse(
        song_id=song_id,
        messages=[ChatHistoryMessage.model_validate(m) for m in messages],
    )


@router.delete("/{song_id}/chat/history", status_code=status.HTTP_200_OK)
async def clear_chat_history(
    song_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    chat_store: Annotated[ChatHistoryStore, Depends(get_chat_history_store)],
):
    """
    Clear all chat history for a song.

    Returns the number of messages deleted.
    """
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    count = await chat_store.clear_history(song_id)
    logger.info(f"Cleared {count} chat messages for song {song_id}")

    return {"deleted": count}


# =============================================================================
# Song Shape / Exploration Endpoints
# =============================================================================


class ShapeChatRequest(BaseModel):
    """Request for chatting with the song shaper."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_CHAT_MESSAGE_LENGTH,
        description="The user's message",
    )
    conversation_history: list[ChatMessageRequest] = Field(
        default_factory=list,
        max_length=MAX_CONVERSATION_HISTORY,
        description="Previous conversation turns",
    )
    llm: Optional[str] = Field(
        None,
        description="LLM to use (e.g., 'ollama/mistral'). Uses default if not specified.",
    )


class KeyImageResponse(BaseModel):
    """A key image in the song shape."""

    text: str
    category: str
    notes: Optional[str] = None


class EmotionalArcResponse(BaseModel):
    """The emotional arc of the song."""

    start: str
    end: str
    turning_point: Optional[str] = None
    notes: Optional[str] = None


class SuggestedSectionResponse(BaseModel):
    """A suggested section in the song shape."""

    type: str
    intent: str
    key_images: list[str] = Field(default_factory=list)


class ReferenceResponse(BaseModel):
    """A reference in the song shape."""

    name: str
    aspect: str


class SongShapeResponse(BaseModel):
    """The full song shape response."""

    theme: str
    theme_notes: Optional[str] = None
    key_images: list[KeyImageResponse] = Field(default_factory=list)
    emotional_arc: EmotionalArcResponse
    references: list[ReferenceResponse] = Field(default_factory=list)
    suggested_structure: list[SuggestedSectionResponse] = Field(default_factory=list)
    raw_fragments: list[str] = Field(default_factory=list)
    conversation_summary: Optional[str] = None
    is_ready: bool = False


@router.post("/{song_id}/shape", response_model=AgentTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def explore_song_shape(
    song_id: UUID,
    request: ShapeChatRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    _credits: Annotated[None, Depends(RequireAICredits())],
):
    """
    Chat with the song shaper to explore and build a song.

    The song shaper agent creates REAL song data as it converses:
    - Creates sections (Verse, Chorus, Bridge, etc.)
    - Adds notes (theme, key images, emotional arc)
    - Updates song metadata

    Changes appear in the song editor immediately.

    Returns immediately with a task_id. Connect to the WebSocket
    at /ws/jobs/{task_id} for real-time streaming responses.

    Special events:
    - `song.updated`: Emitted when the agent creates/updates song data
    """
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    logger.info(f"Starting shape exploration for song '{song.title}' ({song_id})")

    # Convert request history to dict format
    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in request.conversation_history
    ]

    task_id = await run_shaper_task(
        song=song,
        user_message=request.message,
        conversation_history=conversation_history,
        session_factory=get_session,
        user_id=user.id,
        llm=request.llm,
    )

    return AgentTaskResponse(
        task_id=task_id,
        song_id=song_id,
        song_title=song.title,
        task_type="shape_exploration",
        message="Exploration started. Connect to WebSocket for streaming response.",
        websocket_url=f"/ws/jobs/{task_id}",
    )


@router.get("/{song_id}/shape", response_model=SongShapeResponse)
async def get_song_shape(
    song_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """
    Get the current song shape data.

    Returns shape data from song notes, including:
    - Theme
    - Key images and phrases
    - Emotional arc
    - References
    - Raw fragments

    Note: Sections are now created directly during conversation,
    so "suggested_structure" reflects actual created sections.
    """
    await permission_service.require_permission(song_id, user.id, Permission.READ)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    # Extract shape data from song notes
    theme = ""
    theme_notes = None
    key_images = []
    emotional_arc = EmotionalArcResponse(start="", end="")
    references = []
    raw_fragments = []

    if song.song_notes:
        for note in song.song_notes:
            if note.note_type == NoteType.THEME:
                # Theme might have notes after a double newline
                parts = note.content.split("\n\n", 1)
                theme = parts[0]
                if len(parts) > 1:
                    theme_notes = parts[1]

            elif note.note_type == NoteType.KEY_IMAGE:
                # Category is in the title: "Key Image (visual)"
                category = "general"
                if note.title and "(" in note.title:
                    category = note.title.split("(")[1].rstrip(")")
                key_images.append(KeyImageResponse(
                    text=note.content,
                    category=category,
                    notes=None,
                ))

            elif note.note_type == NoteType.EMOTIONAL_ARC:
                # Parse arc from content: "Start: X\nTurning Point: Y\nEnd: Z"
                start = ""
                end = ""
                turning_point = None
                for line in note.content.split("\n"):
                    if line.startswith("Start:"):
                        start = line.replace("Start:", "").strip()
                    elif line.startswith("End:"):
                        end = line.replace("End:", "").strip()
                    elif line.startswith("Turning Point:"):
                        turning_point = line.replace("Turning Point:", "").strip()
                emotional_arc = EmotionalArcResponse(
                    start=start,
                    end=end,
                    turning_point=turning_point,
                )

            elif note.note_type == NoteType.REFERENCE:
                # Parse reference: "Name - Aspect" or just "Name"
                parts = note.content.split(" - ", 1)
                name = parts[0]
                aspect = parts[1] if len(parts) > 1 else ""
                references.append(ReferenceResponse(name=name, aspect=aspect))

            elif note.note_type == NoteType.FRAGMENT:
                raw_fragments.append(note.content)

    # Build structure from actual sections (they're created directly now)
    suggested_structure = [
        SuggestedSectionResponse(
            type=section.type.value,
            intent=section.notes or "",
            key_images=[],
        )
        for section in sorted(song.sections, key=lambda s: s.order)
    ]

    # Song is ready for writing if it has sections
    is_ready = len(song.sections) > 0

    return SongShapeResponse(
        theme=theme,
        theme_notes=theme_notes,
        key_images=key_images,
        emotional_arc=emotional_arc,
        references=references,
        suggested_structure=suggested_structure,
        raw_fragments=raw_fragments,
        conversation_summary=None,  # Not stored separately anymore
        is_ready=is_ready,
    )


# Note: finalize_song_shape endpoint removed - sections are now created
# directly during the shaper conversation using the create_sections tool
