"""
LangGraph workflow for agent orchestration with streaming.

This module provides the "how" - orchestrating agent execution and streaming
real-time updates to WebSocket clients.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, AsyncIterator, Callable
from uuid import UUID

from langgraph.graph import StateGraph, START, END
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

from api.models import Song
from api.agents.critic import (
    critic_agent,
    CriticDependencies,
    FULL_REVIEW_PROMPT,
    CLICHE_CHECK_PROMPT,
    RHYTHM_ANALYSIS_PROMPT,
    SECTION_REVIEW_PROMPT,
)
from api.agents.orchestrator import (
    orchestrator_agent,
    OrchestratorDependencies,
    build_orchestrator_prompt,
    build_system_prompt,
    SessionFactory,
)

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Types of agent tasks."""
    FULL_REVIEW = "full_review"
    CHECK_CLICHES = "check_cliches"
    ANALYZE_RHYTHM = "analyze_rhythm"
    SECTION_REVIEW = "section_review"


@dataclass
class AgentEvent:
    """An event from agent execution for streaming."""
    event_type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentResult:
    """Result from an agent task."""
    result: str
    success: bool = True
    error_message: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_cost_usd: Decimal = Decimal("0")
    duration_ms: int = 0
    model: str | None = None


@dataclass
class WorkflowState:
    """State for the agent workflow."""
    # Input
    song: Song
    task_type: TaskType
    section_index: int | None = None
    model: str | None = None

    # Progress tracking
    events: list[AgentEvent] = field(default_factory=list)
    current_step: str = "initializing"

    # Output
    result: AgentResult | None = None


async def run_critic_workflow(
    song: Song,
    task_type: TaskType,
    section_index: int | None = None,
    model: str | None = None,
    on_event: Callable[[AgentEvent], None] | None = None,
) -> AgentResult:
    """
    Run the critic agent workflow with streaming events.

    Args:
        song: The song to analyze
        task_type: Type of analysis to perform
        section_index: Section index for section reviews
        model: Optional model override (e.g., "ollama/mistral")
        on_event: Callback for streaming events

    Returns:
        AgentResult with the analysis and metrics
    """
    start_time = time.time()

    def emit(event_type: str, data: dict[str, Any]):
        """Emit an event to the callback."""
        event = AgentEvent(event_type=event_type, data=data)
        if on_event:
            on_event(event)

    try:
        # Emit start event
        emit("agent.started", {
            "agent_name": "Constructive Music Critic",
            "task_type": task_type.value,
            "song_title": song.title,
        })

        # Build the prompt based on task type
        prompt = _build_prompt(song, task_type, section_index)

        emit("agent.thinking", {"thought": f"Analyzing '{song.title}'..."})

        # Create dependencies
        deps = CriticDependencies(song=song)

        # Run the agent with streaming events
        result_text = ""
        input_tokens = 0
        output_tokens = 0
        final_result = None

        # Use run_stream_events for rich event information
        async for event in critic_agent.run_stream_events(
            prompt,
            deps=deps,
            model=model,  # Override model if provided
        ):
            event_kind = getattr(event, 'event_kind', None)

            if event_kind == 'function_tool_call':
                # Tool call started
                tool_name = event.part.tool_name if hasattr(event, 'part') else 'unknown'
                emit("agent.tool.start", {"tool_name": tool_name})
                emit("agent.thinking", {"thought": f"Using {tool_name}..."})

            elif event_kind == 'function_tool_result':
                # Tool returned result
                tool_name = getattr(event.result, 'tool_name', 'unknown') if hasattr(event, 'result') else 'unknown'
                # Get a preview of the result content
                content_preview = str(event.content)[:100] if hasattr(event, 'content') and event.content else "completed"
                emit("agent.tool.end", {"tool_name": tool_name, "tool_output": content_preview})

            elif event_kind == 'part_delta':
                # Streaming text delta
                if hasattr(event, 'delta'):
                    delta = event.delta
                    # TextPartDelta has a 'content_delta' attribute
                    text = getattr(delta, 'content_delta', '') or getattr(delta, 'content', '')
                    if text:
                        result_text += text
                        emit("agent.chunk", {"text": text})

            elif event_kind == 'part_start':
                # A new part is starting (text, tool call, etc.)
                part = getattr(event, 'part', None)
                if part:
                    part_kind = getattr(part, 'part_kind', None)
                    if part_kind == 'text' and hasattr(part, 'content'):
                        # Initial text content
                        text = part.content
                        if text:
                            result_text += text
                            emit("agent.chunk", {"text": text})

            elif event_kind == 'agent_run_result':
                # Final result event
                final_result = event.result
                # Extract usage info
                if hasattr(final_result, 'usage'):
                    usage = final_result.usage()
                    if usage:
                        input_tokens = getattr(usage, 'request_tokens', 0) or 0
                        output_tokens = getattr(usage, 'response_tokens', 0) or 0

        # If we didn't accumulate text but have a final result, use that
        if not result_text and final_result:
            output = final_result.output if hasattr(final_result, 'output') else final_result
            result_text = str(output)

        duration_ms = int((time.time() - start_time) * 1000)

        # Estimate cost (rough estimates)
        total_cost = _estimate_cost(input_tokens, output_tokens, model)

        emit("agent.completed", {
            "result": result_text[:500] + "..." if len(result_text) > 500 else result_text,
            "duration_ms": duration_ms,
        })

        return AgentResult(
            result=result_text,
            success=True,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=total_cost,
            duration_ms=duration_ms,
            model=model or "openai:gpt-5.2",
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Agent workflow failed: {e}")

        emit("agent.failed", {"error": str(e)})

        return AgentResult(
            result="",
            success=False,
            error_message=str(e),
            duration_ms=duration_ms,
            model=model or "openai:gpt-5.2",
        )


def _build_prompt(song: Song, task_type: TaskType, section_index: int | None) -> str:
    """Build the prompt based on task type."""
    if task_type == TaskType.FULL_REVIEW:
        return FULL_REVIEW_PROMPT.format(title=song.title)

    elif task_type == TaskType.CHECK_CLICHES:
        return CLICHE_CHECK_PROMPT.format(title=song.title)

    elif task_type == TaskType.ANALYZE_RHYTHM:
        return RHYTHM_ANALYSIS_PROMPT.format(title=song.title)

    elif task_type == TaskType.SECTION_REVIEW:
        if section_index is None or section_index >= len(song.sections):
            raise ValueError(f"Invalid section index: {section_index}")

        section = song.sections[section_index]
        section_type = section.type.value
        if section.number:
            section_type += f" {section.number}"

        section_lyrics = "\n".join(line.text for line in section.lines)

        return SECTION_REVIEW_PROMPT.format(
            title=song.title,
            section_type=section_type,
            section_lyrics=section_lyrics,
        )

    else:
        raise ValueError(f"Unknown task type: {task_type}")


def _estimate_cost(input_tokens: int, output_tokens: int, model: str | None) -> Decimal:
    """Estimate cost based on tokens and model."""
    # Default rates per 1K tokens (GPT-4o-mini)
    input_rate = Decimal("0.00015")  # $0.15 per 1M
    output_rate = Decimal("0.0006")  # $0.60 per 1M

    # Adjust for different models
    if model and "gpt-4o" in model and "mini" not in model:
        input_rate = Decimal("0.005")
        output_rate = Decimal("0.015")
    elif model and "ollama" in model:
        # Local models are free
        return Decimal("0")

    input_cost = (Decimal(input_tokens) / 1000) * input_rate
    output_cost = (Decimal(output_tokens) / 1000) * output_rate

    return input_cost + output_cost


# Tools that modify song data - emit song.updated event for these
SONG_MODIFICATION_TOOLS = frozenset([
    'set_theme', 'add_key_image', 'set_emotional_arc',
    'create_sections', 'add_fragment', 'add_reference',
    'update_song_title', 'write_lyrics', 'update_lyrics',
    # New structure control tools
    'delete_section', 'delete_sections', 'move_section',
    'reorder_sections', 'replace_structure',
    'write_to_slot', 'replace_slot_lyrics',
])


async def run_orchestrator_workflow(
    song: Song,
    user_message: str,
    conversation_history: list[dict],
    session_factory: SessionFactory,
    model: str | None = None,
    on_event: Callable[[AgentEvent], None] | None = None,
) -> AgentResult:
    """
    Run the unified orchestrator agent for all songwriting tasks.

    The orchestrator adapts its behavior based on context:
    - Exploration: Asks questions, builds understanding
    - Writing: Creates sections, drafts lyrics
    - Refinement: Gives feedback, improves content

    Args:
        song: The song context
        user_message: The current user message
        conversation_history: Previous conversation turns [{role, content}]
        session_factory: Factory for creating database sessions (for concurrent tool calls)
        model: Optional model override
        on_event: Callback for streaming events

    Returns:
        AgentResult with the response and metrics
    """
    start_time = time.time()

    def emit(event_type: str, data: dict[str, Any]):
        """Emit an event to the callback."""
        event = AgentEvent(event_type=event_type, data=data)
        if on_event:
            on_event(event)

    try:
        emit("agent.started", {
            "agent_name": "Songwriting Collaborator",
            "task_type": "chat",
            "song_title": song.title,
        })

        # Build context-aware system prompt
        system_prompt = build_system_prompt(song, conversation_history)

        # Build the user prompt with conversation history
        prompt = build_orchestrator_prompt(user_message, conversation_history, song)

        emit("agent.thinking", {"thought": "Thinking about your song..."})

        # Create dependencies with session factory for tools that modify song data
        # The system prompt is passed via dependencies for dynamic context
        deps = OrchestratorDependencies(
            song=song,
            session_factory=session_factory,
            conversation_history=conversation_history,
            system_prompt=system_prompt,  # Context-aware prompt via dependencies
        )

        # Run the agent with streaming
        result_text = ""
        input_tokens = 0
        output_tokens = 0
        final_result = None

        tools_called = []

        async for event in orchestrator_agent.run_stream_events(
            prompt,
            deps=deps,
            model=model,
        ):
            event_kind = getattr(event, 'event_kind', None)

            if event_kind == 'function_tool_call':
                tool_name = event.part.tool_name if hasattr(event, 'part') else 'unknown'
                tools_called.append(tool_name)
                logger.info(f"Tool called: {tool_name}")
                emit("agent.tool.start", {"tool_name": tool_name})
                emit("agent.thinking", {"thought": f"Using {tool_name}..."})

            elif event_kind == 'function_tool_result':
                tool_name = getattr(event.result, 'tool_name', 'unknown') if hasattr(event, 'result') else 'unknown'
                content_preview = str(event.content)[:100] if hasattr(event, 'content') and event.content else "completed"
                emit("agent.tool.end", {"tool_name": tool_name, "tool_output": content_preview})

                # Emit song update event when song modification tools are used
                if tool_name in SONG_MODIFICATION_TOOLS:
                    emit("song.updated", {"tool_name": tool_name})

            elif event_kind == 'part_delta':
                if hasattr(event, 'delta'):
                    delta = event.delta
                    text = getattr(delta, 'content_delta', '') or getattr(delta, 'content', '')
                    if text:
                        result_text += text
                        emit("agent.chunk", {"text": text})

            elif event_kind == 'part_start':
                part = getattr(event, 'part', None)
                if part:
                    part_kind = getattr(part, 'part_kind', None)
                    if part_kind == 'text' and hasattr(part, 'content'):
                        text = part.content
                        if text:
                            result_text += text
                            emit("agent.chunk", {"text": text})

            elif event_kind == 'agent_run_result':
                final_result = event.result
                if hasattr(final_result, 'usage'):
                    usage = final_result.usage()
                    if usage:
                        input_tokens = getattr(usage, 'request_tokens', 0) or 0
                        output_tokens = getattr(usage, 'response_tokens', 0) or 0

        if not result_text and final_result:
            output = final_result.output if hasattr(final_result, 'output') else final_result
            result_text = str(output)

        duration_ms = int((time.time() - start_time) * 1000)
        total_cost = _estimate_cost(input_tokens, output_tokens, model)

        # Log summary of tools used
        if tools_called:
            logger.info(f"Orchestrator used {len(tools_called)} tools: {', '.join(tools_called)}")
        else:
            logger.warning(f"Orchestrator returned without calling any tools. Message: {user_message[:100]}")

        emit("agent.completed", {
            "result": result_text[:500] + "..." if len(result_text) > 500 else result_text,
            "duration_ms": duration_ms,
        })

        return AgentResult(
            result=result_text,
            success=True,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=total_cost,
            duration_ms=duration_ms,
            model=model or "openai:gpt-5.2",
        )

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Orchestrator workflow failed: {e}")

        emit("agent.failed", {"error": str(e)})

        return AgentResult(
            result="",
            success=False,
            error_message=str(e),
            duration_ms=duration_ms,
            model=model or "openai:gpt-5.2",
        )


# Alias for backward compatibility - both now use the same unified orchestrator
run_shaper_workflow = run_orchestrator_workflow
