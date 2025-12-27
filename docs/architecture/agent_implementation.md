# Agent Implementation Guide

> **Practical guide to building songwriter agents with CrewAI.**

See also: [Multi-Agent Architecture](./multi_agent.md) for design patterns.

---

## Current vs Agent Approach

| Pattern | Flow | Example |
|---------|------|---------|
| **Request-Response** | User asks → LLM responds → Done | "Suggest structure" → one suggestion |
| **Goal-Oriented Agent** | User sets goal → Agent plans → Acts → Reflects → Iterates → Delivers | "Help me finish this song" → polished draft |

```
Agent: Plans approach → Analyzes lyrics → Identifies weak spots →
       Suggests improvements → Evaluates results → Iterates →
       Delivers polished draft
```

---

## Framework Comparison

| Framework | Fit | Pros | Cons |
|-----------|-----|------|------|
| **CrewAI** | ⭐⭐⭐⭐⭐ | Role-based agents perfect for creative collaboration, 30k+ stars, production-ready | Newer, less control over internals |
| **LangGraph** | ⭐⭐⭐⭐ | Most mature, graph-based state machines, best observability | Heavier, steeper learning curve |
| **Pydantic AI** | ⭐⭐⭐⭐ | Type-safe, fits our stack, lightweight | Less multi-agent coordination |
| **Claude Agent SDK** | ⭐⭐⭐ | Powers Claude Code, Anthropic-native | Tied to Claude, newer |
| **Custom** | ⭐⭐⭐ | Full control, no dependencies | More work, reinvent the wheel |

**Recommendation:** CrewAI + Custom Hybrid

CrewAI's role-based model maps perfectly to songwriting collaboration.

---

## Agent Use Cases

### 1. Co-Writing Agent

```
Goal: "Help me write a verse about heartbreak"

Agent workflow:
  1. Analyzes existing song context (key, feel, existing lyrics)
  2. Generates 5 variations
  3. Self-critiques each for rhythm, rhyme, emotion
  4. Refines the best one
  5. Presents top 2-3 options with reasoning
```

### 2. Song Review Agent

```
Goal: "Review my song and suggest improvements"

Agent workflow:
  1. Analyzes structure (is it balanced?)
  2. Checks rhyme schemes (consistent?)
  3. Evaluates syllable counts (singable?)
  4. Identifies clichés
  5. Suggests specific line replacements
  6. Compiles report with prioritized fixes
```

### 3. Research Agent

```
Goal: "Find chord progressions that match this mood"

Agent workflow:
  1. Analyzes song's emotional tone
  2. Searches music theory resources
  3. Finds similar songs for reference
  4. Suggests 3-4 progressions with examples
  5. Explains why each works
```

### 4. Multi-Agent Collaboration

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Lyricist  │ ←→  │  Structure  │ ←→  │   Critic    │
│    Agent    │     │    Agent    │     │    Agent    │
└─────────────┘     └─────────────┘     └─────────────┘
        ↓                   ↓                   ↓
                    Final Song
```

---

## Architecture

```
api/
├── agents/
│   ├── __init__.py
│   ├── base.py              # Base agent configuration
│   ├── lyricist.py          # Lyric generation agent
│   ├── structure.py         # Structure analysis agent
│   ├── critic.py            # Review/feedback agent
│   ├── melody.py            # Chord/melody agent
│   ├── crews/
│   │   ├── cowrite_crew.py  # Full co-writing session
│   │   ├── review_crew.py   # Song review workflow
│   │   └── polish_crew.py   # Final polish workflow
│   └── tools/               # Agent tools
│       ├── rhyme_finder.py
│       ├── syllable_counter.py
│       ├── chord_suggester.py
│       ├── cliche_detector.py
│       └── song_db_tool.py
│
├── flows/                   # CrewAI Flows for deterministic paths
│   ├── new_song_flow.py
│   ├── improve_section_flow.py
│   └── finalize_flow.py
│
├── services/
│   ├── agent_service.py     # Orchestrates agent sessions
│   └── session_manager.py   # Manage ongoing sessions
```

---

## Agent Roles

```python
# api/agents/roles.py

SONGWRITER_AGENTS = {
    "lyricist": {
        "role": "Expert Lyricist",
        "goal": "Write compelling, emotionally resonant lyrics that fit the song's theme and structure",
        "backstory": """You're a veteran songwriter with decades of experience writing
        hit songs across genres. You understand rhythm, meter, rhyme schemes, and how
        to craft lyrics that connect with listeners. You balance creativity with
        singability.""",
        "tools": ["rhyme_finder", "syllable_counter", "emotion_analyzer"],
    },

    "structure": {
        "role": "Song Structure Architect",
        "goal": "Design song structures that create emotional journeys and maintain listener engagement",
        "backstory": """You've studied thousands of hit songs and understand what makes
        structures work. You know when a bridge lifts a song, when a pre-chorus builds
        tension, and how to pace verses and choruses for maximum impact.""",
        "tools": ["structure_analyzer", "song_database"],
    },

    "critic": {
        "role": "Constructive Music Critic",
        "goal": "Provide honest, actionable feedback that improves songs without crushing creativity",
        "backstory": """You're a respected A&R executive and music journalist who's
        developed hundreds of artists. You have high standards but know how to give
        feedback that inspires improvement rather than discouragement.""",
        "tools": ["cliche_detector", "originality_scorer", "commercial_analyzer"],
    },

    "melody": {
        "role": "Melody & Harmony Specialist",
        "goal": "Suggest chord progressions and melodic ideas that enhance the emotional impact",
        "backstory": """You're a music theory expert and producer who understands how
        harmony supports lyrics. You can suggest progressions that match any mood and
        know what makes melodies memorable.""",
        "tools": ["chord_suggester", "key_analyzer", "progression_database"],
    },
}
```

---

## Simple Agent Pattern

Without a framework, the core pattern is:

```python
class SongwriterAgent:
    """Base agent that can plan, act, and reflect."""

    def __init__(self, llm: BaseLLMProvider, tools: list[Tool]):
        self.llm = llm
        self.tools = tools

    async def run(self, goal: str, song: Song, max_iterations: int = 5):
        context = {"goal": goal, "song": song, "history": []}

        for i in range(max_iterations):
            # 1. Plan next action
            plan = await self.plan(context)

            # 2. Execute action (might use tools)
            result = await self.act(plan)

            # 3. Reflect on result
            evaluation = await self.reflect(result, context)

            # 4. Check if goal achieved
            if evaluation.goal_achieved:
                return result

            context["history"].append({"plan": plan, "result": result})

        return self.best_result(context)
```

---

## Implementation Phases

### Phase 1: Foundation

```bash
uv add crewai crewai-tools
```

```python
# api/agents/base.py
from crewai import Agent, Task, Crew
from api.llm import get_provider

class SongwriterAgentBase:
    """Base configuration for all songwriter agents."""

    def __init__(self, llm_provider=None):
        self.llm = llm_provider or get_provider()

    def create_agent(self, role_config: dict) -> Agent:
        return Agent(
            role=role_config["role"],
            goal=role_config["goal"],
            backstory=role_config["backstory"],
            tools=self._load_tools(role_config["tools"]),
            llm=self.llm,
            verbose=True,
            memory=True,  # Remember context within session
        )
```

### Phase 2: Core Agents

```python
# api/agents/crews/cowrite_crew.py
from crewai import Crew, Task, Process

class CowriteCrew:
    """Multi-agent crew for collaborative songwriting."""

    def __init__(self, song: Song):
        self.song = song
        self.lyricist = create_lyricist_agent()
        self.structure = create_structure_agent()
        self.critic = create_critic_agent()

    def write_section(self, section_type: str, context: str) -> CrewOutput:
        """Collaboratively write a new section."""

        # Task 1: Lyricist drafts
        draft_task = Task(
            description=f"""Write a {section_type} for this song.

            Song context: {self.song.get_full_lyrics()}
            Theme/direction: {context}
            Key: {self.song.key}, Feel: {self.song.feel}

            Write 3 variations.""",
            expected_output="Three lyric variations with explanations",
            agent=self.lyricist,
        )

        # Task 2: Critic evaluates
        critique_task = Task(
            description="""Review the lyric variations.
            Evaluate: rhythm, imagery, originality, singability.
            Pick the best one and suggest specific improvements.""",
            expected_output="Selected variation with improvement suggestions",
            agent=self.critic,
            context=[draft_task],
        )

        # Task 3: Lyricist refines
        refine_task = Task(
            description="""Apply the critic's feedback to polish the lyrics.
            Ensure the final version is radio-ready.""",
            expected_output="Final polished lyrics",
            agent=self.lyricist,
            context=[draft_task, critique_task],
        )

        crew = Crew(
            agents=[self.lyricist, self.critic],
            tasks=[draft_task, critique_task, refine_task],
            process=Process.sequential,
            verbose=True,
        )

        return crew.kickoff()
```

### Phase 3: Tools

```python
# api/agents/tools/rhyme_finder.py
from crewai.tools import BaseTool

class RhymeFinderTool(BaseTool):
    name: str = "Rhyme Finder"
    description: str = "Find rhymes for a word. Input: word to rhyme. Returns: list of rhymes."

    def _run(self, word: str) -> str:
        import httpx
        response = httpx.get(f"https://api.datamuse.com/words?rel_rhy={word}&max=20")
        rhymes = [r["word"] for r in response.json()]
        return f"Rhymes for '{word}': {', '.join(rhymes)}"


class SyllableCounterTool(BaseTool):
    name: str = "Syllable Counter"
    description: str = "Count syllables in a line. Input: text line. Returns: syllable count."

    def _run(self, text: str) -> str:
        import pronouncing
        words = text.split()
        total = sum(
            len(pronouncing.phones_for_word(w)[0].split())
            for w in words if pronouncing.phones_for_word(w)
        )
        return f"'{text}' has approximately {total} syllables"


class SongDatabaseTool(BaseTool):
    name: str = "Song Database"
    description: str = "Access the current song's data. Input: 'full_lyrics', 'sections', 'metadata'"

    def __init__(self, song: Song):
        super().__init__()
        self.song = song

    def _run(self, query: str) -> str:
        if query == "full_lyrics":
            return self.song.get_full_lyrics()
        elif query == "sections":
            return str([{"type": s.type, "lines": s.lines_data} for s in self.song.sections])
        elif query == "metadata":
            return f"Key: {self.song.key}, Tempo: {self.song.tempo}, Feel: {self.song.feel}"
```

### Phase 4: API Integration

```python
# api/routes/agents.py
from fastapi import APIRouter, WebSocket
from api.agents.crews import CowriteCrew, ReviewCrew

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("/{song_id}/cowrite")
async def start_cowrite_session(
    song_id: UUID,
    request: CowriteRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Start a co-writing session with AI agents."""
    song = await store.get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    job_id = await job_manager.enqueue(
        "cowrite_session",
        song_id=str(song_id),
        section_type=request.section_type,
        context=request.context,
    )

    return {"job_id": job_id, "message": "Co-writing session started"}


@router.post("/{song_id}/review")
async def review_song(song_id: UUID):
    """Start a song review session."""
    job_id = await job_manager.enqueue("review_agent", song_id=str(song_id))
    return {"job_id": job_id}


@router.websocket("/{song_id}/session")
async def agent_session_websocket(websocket: WebSocket, song_id: UUID):
    """Real-time agent session with streaming updates."""
    await websocket.accept()

    async for update in agent_session_stream(song_id):
        await websocket.send_json({
            "agent": update.agent_name,
            "action": update.action,
            "content": update.content,
            "timestamp": update.timestamp,
        })
```

### Phase 5: Production Hardening

```python
# api/services/agent_service.py
import asyncio
import time
from uuid import UUID

from api.billing import CostTracker


class AgentService:
    """Production-ready agent orchestration."""

    def __init__(
        self,
        cost_tracker: CostTracker,
        max_iterations: int = 10,
        timeout_seconds: int = 300,
    ):
        self.cost_tracker = cost_tracker
        self.max_iterations = max_iterations
        self.timeout = timeout_seconds

    async def run_crew(
        self,
        crew: Crew,
        user_id: UUID,
        song_id: UUID,
    ) -> AgentResult:
        """Run a crew with production safeguards."""

        start_time = time.time()
        total_cost = 0.0

        try:
            def on_llm_call(tokens_in, tokens_out, model):
                nonlocal total_cost
                cost = self.cost_tracker.calculate_cost(tokens_in, tokens_out, model)
                total_cost += cost

                if total_cost > settings.MAX_AGENT_COST_PER_SESSION:
                    raise AgentBudgetExceededError(
                        f"Session cost ${total_cost:.2f} exceeds limit"
                    )

            result = await asyncio.wait_for(
                crew.kickoff_async(),
                timeout=self.timeout
            )

            await self.log_session(
                user_id=user_id,
                song_id=song_id,
                crew_type=crew.__class__.__name__,
                duration=time.time() - start_time,
                cost=total_cost,
                success=True,
            )

            return AgentResult(
                success=True,
                output=result,
                cost=total_cost,
                duration=time.time() - start_time,
            )

        except asyncio.TimeoutError:
            return AgentResult(success=False, error="Session timed out")
        except AgentBudgetExceededError as e:
            return AgentResult(success=False, error=str(e))
```

---

## Production Considerations

### Cost Management

```python
# Track and limit costs per user/session
AGENT_COST_LIMITS = {
    "free_tier": 0.50,      # $0.50 per session
    "pro_tier": 5.00,       # $5.00 per session
    "unlimited": None,
}
```

### Queue Management

```python
# Use ARQ with priorities
async def enqueue_agent_task(task_type: str, priority: int = 5, **kwargs):
    """Enqueue agent task with priority (1=highest, 10=lowest)."""
    await arq_pool.enqueue_job(
        task_type,
        _queue_name=f"agents_priority_{priority}",
        **kwargs
    )
```

### Caching

```python
# Cache common agent outputs
@cached(ttl=3600, key="rhymes:{word}")
async def get_rhymes(word: str) -> list[str]:
    ...

# Cache song analysis (expensive)
@cached(ttl=86400, key="analysis:{song_hash}")
async def analyze_song_structure(song: Song) -> StructureAnalysis:
    ...
```

### Observability

```python
# Integrate with LangFuse for tracing
from langfuse import Langfuse

langfuse = Langfuse()

@langfuse.trace()
async def run_cowrite_session(song_id: UUID, context: str):
    # All LLM calls automatically traced
    ...
```

---

## Benefits Summary

| Benefit | Example |
|---------|---------|
| **Iteration** | Agent refines lyrics through multiple passes |
| **Tool Use** | Agent can search rhyme databases, chord charts |
| **Memory** | Agent remembers what worked/didn't across session |
| **Autonomy** | "Finish this song" vs "suggest one line" |
| **Quality** | Self-critique catches issues before user sees |

---

## Starting Point Recommendation

1. **Install CrewAI**: `uv add crewai crewai-tools`
2. **Build one agent first**: Start with Critic - useful standalone for reviewing songs
3. **Add tools incrementally**: Rhyme finder → Syllable counter → Song DB access
4. **Then build crews**: Combine agents into workflows
5. **Add production hardening**: Cost limits, timeouts, observability

---

## Related Documentation

- [Multi-Agent Architecture](./multi_agent.md) - Design patterns and concepts
- [AI Interaction Modes](../product/ai_interaction_modes.md) - How users interact with agents
- [Architecture Patterns](./patterns.md) - Service layer, background jobs
