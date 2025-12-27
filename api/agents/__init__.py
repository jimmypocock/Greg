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
]
