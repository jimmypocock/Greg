"""
Songwriter agents using PydanticAI and LangGraph.

This package provides AI agents for analyzing and providing feedback on songs.
"""

from api.agents.workflow import (
    AgentResult,
    AgentEvent,
    TaskType,
    run_critic_workflow,
)
from api.agents.critic import (
    critic_agent,
    CriticDependencies,
    SongReview,
)
from api.agents.song_shaper import (
    song_shaper_agent,
    SongShaperDependencies,
    build_shaper_prompt,
)

__all__ = [
    # Workflow
    "AgentResult",
    "AgentEvent",
    "TaskType",
    "run_critic_workflow",
    # Critic agent
    "critic_agent",
    "CriticDependencies",
    "SongReview",
    # Song shaper agent
    "song_shaper_agent",
    "SongShaperDependencies",
    "build_shaper_prompt",
]
