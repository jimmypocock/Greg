# Multi-Agent Architecture for Songwriting Platform

> **Status:** Theoretical / Future Vision
> **Priority:** Long-term roadmap
> **Complexity:** High
> **Inspiration:** AI-powered creative studio with specialized agents

## Vision

Transform the platform from a single AI assistant into a **virtual creative team** — multiple specialized agents that collaborate to help users through the entire songwriting and music career journey.

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER'S CREATIVE STUDIO                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│   │  Songwriter │  │  Producer   │  │   Critic    │            │
│   │   Partner   │  │   Agent     │  │   Agent     │            │
│   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘            │
│          │                │                │                    │
│          └────────────────┼────────────────┘                    │
│                           │                                     │
│                    ┌──────▼──────┐                              │
│                    │ Orchestrator │                             │
│                    └──────┬──────┘                              │
│                           │                                     │
│   ┌─────────────┐  ┌──────▼──────┐  ┌─────────────┐            │
│   │   Manager   │  │    Coach    │  │  Researcher │            │
│   │   Agent     │  │    Agent    │  │    Agent    │            │
│   └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Roles

### 1. Songwriter Partner Agent

**Role:** Creative collaborator for lyrics, melody, and structure

**Personality:** Encouraging, creative, pushes boundaries while respecting user's vision

**Capabilities:**
- Co-write lyrics line by line
- Suggest rhymes, metaphors, imagery
- Help develop song concepts/themes
- Brainstorm hooks and titles
- Restructure sections for flow

**Tools:**
```python
songwriter_tools = [
    "search_rhymes",           # Find rhyming words
    "find_synonyms",           # Alternative word choices
    "analyze_meter",           # Check syllable patterns
    "get_song_context",        # Current song state
    "suggest_imagery",         # Generate metaphor ideas
    "find_similar_songs",      # Reference inspiration
]
```

**Example Interaction:**
```
User: "I'm stuck on the second verse. It's about leaving home."

Songwriter Agent:
  → Calls get_song_context() to see verse 1 and chorus
  → Calls find_similar_songs("leaving home", "departure")
  → Reasons: V1 establishes the setting, chorus is emotional peak
  → Suggests: "V2 should show the moment of decision - the last look back"
  → Offers 3 opening line options with different emotional angles
```

---

### 2. Producer Agent

**Role:** Sonic and arrangement advisor

**Personality:** Technical but accessible, genre-aware, focused on the listener experience

**Capabilities:**
- Suggest chord progressions
- Recommend song structure for genre
- Advise on dynamics and energy flow
- Suggest instrumentation
- Identify production references

**Tools:**
```python
producer_tools = [
    "analyze_chord_progression",  # Evaluate harmonic choices
    "suggest_chords",             # Generate progressions
    "get_genre_conventions",      # Genre-specific patterns
    "analyze_energy_arc",         # Song dynamics
    "find_reference_tracks",      # Similar production styles
    "estimate_tempo_key",         # From audio if uploaded
]
```

**Example Interaction:**
```
User: "Does this chord progression work for an indie folk song?"

Producer Agent:
  → Calls analyze_chord_progression([Am, F, C, G])
  → Calls get_genre_conventions("indie folk")
  → Reasons: Progression is solid but very common
  → Suggests: "Try Am → Fmaj7 → C → G/B for more movement"
  → Provides audio reference: "Similar vibe to Bon Iver's 'Skinny Love'"
```

---

### 3. Critic Agent

**Role:** Constructive feedback and quality assessment (already exists)

**Personality:** Configurable (encouraging mentor → tough love), honest, specific

**Capabilities:**
- Evaluate lyrics for clarity, imagery, emotion
- Assess structure and pacing
- Identify weak points
- Compare to user's goals
- Track improvement over time

**Tools:**
```python
critic_tools = [
    "analyze_lyrics",           # Deep lyric analysis
    "check_cliches",            # Flag overused phrases
    "evaluate_structure",       # Assess song form
    "compare_to_goals",         # User's stated intentions
    "get_revision_history",     # Track changes over time
]
```

---

### 4. Coach Agent

**Role:** Skill development and learning

**Personality:** Patient teacher, celebrates progress, provides exercises

**Capabilities:**
- Identify skill gaps
- Suggest exercises and prompts
- Explain songwriting concepts
- Provide historical/educational context
- Track learning progress

**Tools:**
```python
coach_tools = [
    "assess_skill_level",       # Evaluate user's writing
    "generate_exercise",        # Create practice prompts
    "explain_technique",        # Educational content
    "get_learning_history",     # Past lessons/progress
    "find_examples",            # Songs demonstrating techniques
]
```

**Example Interaction:**
```
User: "My verses always feel boring compared to my choruses"

Coach Agent:
  → Calls get_learning_history() to see past feedback
  → Calls assess_skill_level("verse writing")
  → Identifies: User's verses lack melodic variation
  → Explains: Verse vs chorus contrast techniques
  → Generates: 3 exercises for varying verse melody
  → Assigns: "Try rewriting your latest verse with this constraint..."
```

---

### 5. Manager Agent

**Role:** Career and release planning

**Personality:** Professional, strategic, organized, business-minded

**Capabilities:**
- Plan release schedules
- Suggest marketing strategies
- Track goals and milestones
- Organize catalog
- Provide industry insights

**Tools:**
```python
manager_tools = [
    "get_catalog",              # User's song library
    "create_release_plan",      # Schedule releases
    "analyze_market_trends",    # Genre/timing insights
    "set_goals",                # Career milestones
    "track_progress",           # Goal completion
    "suggest_collaborations",   # Potential co-writers
]
```

**Example Interaction:**
```
User: "I want to release an EP by summer"

Manager Agent:
  → Calls get_catalog() to see completed/in-progress songs
  → Reasons: 3 songs ready, 2 in progress, need 5-6 for EP
  → Creates timeline: Finish writing by March, production April, release June
  → Suggests: "Focus on completing 'Empty Chair' and 'Neon Signs' next"
  → Sets milestones with check-in dates
```

---

### 6. Researcher Agent

**Role:** Information gathering and analysis

**Personality:** Thorough, factual, provides sources

**Capabilities:**
- Research song topics
- Find historical/cultural context
- Analyze trends
- Competitive analysis
- Gather inspiration

**Tools:**
```python
researcher_tools = [
    "web_search",               # External research
    "analyze_lyrics_corpus",    # Study existing songs
    "get_artist_info",          # Artist backgrounds
    "find_cultural_context",    # Historical references
    "trend_analysis",           # What's popular now
]
```

---

## Tool Schemas & Data Formatting

### Why Schemas Matter

Agents call tools and reason about results. **Structured outputs** ensure reliable data exchange:

```python
from pydantic import BaseModel

# Tool input schema
class SearchRhymesInput(BaseModel):
    word: str
    max_results: int = 10
    rhyme_type: Literal["perfect", "near", "slant"] = "perfect"

# Tool output schema
class RhymeResult(BaseModel):
    word: str
    rhymes: list[str]
    syllable_counts: dict[str, int]

# Chord analysis output
class ChordAnalysis(BaseModel):
    chords: list[str]
    key: str
    mode: Literal["major", "minor"]
    genre_fit: list[str]
    tension_level: int  # 1-10
    suggestions: list[str]

# Meter analysis output
class MeterAnalysis(BaseModel):
    syllable_count: int
    stress_pattern: list[Literal["S", "U"]]  # Stressed/Unstressed
    meter_type: str | None  # "iambic", "trochaic", etc.
    fits_melody: bool
```

**Benefits:**
- Agent can reliably access `result.tension_level` vs parsing messy text
- Validation catches errors early
- IDE autocomplete and type checking
- Self-documenting tool interfaces

### Data-to-Text Conversion

LLMs reason better with **prose** than raw JSON. Convert structured data before injecting into prompts:

```python
class Song(BaseModel):
    title: str
    sections: list[Section]
    mood_tags: list[str]
    chord_progression: list[str]

    def to_prompt_text(self) -> str:
        """Convert to readable text for LLM context."""
        section_summary = " → ".join(s.type for s in self.sections)
        total_lines = sum(len(s.lines) for s in self.sections)

        return f"""
Song: "{self.title}"
Mood: {", ".join(self.mood_tags)}
Structure: {section_summary}
Length: {total_lines} lines across {len(self.sections)} sections
Chords: {" → ".join(self.chord_progression)}
""".strip()


class ChordAnalysis(BaseModel):
    chords: list[str]
    key: str
    tension_level: int
    suggestions: list[str]

    def to_prompt_text(self) -> str:
        """Convert analysis to readable text."""
        return f"""
Chord Analysis:
- Progression: {" → ".join(self.chords)}
- Key: {self.key}
- Tension level: {self.tension_level}/10
- Suggestions: {"; ".join(self.suggestions) if self.suggestions else "None"}
""".strip()


class UserPreferences(BaseModel):
    genres: list[str]
    influences: str
    feedback_style: str
    experience_level: str

    def to_prompt_text(self) -> str:
        """Convert preferences to prompt context."""
        style_descriptions = {
            "encouraging": "Be encouraging and supportive. Lead with strengths.",
            "balanced": "Balance praise with constructive criticism.",
            "tough_love": "Be direct and honest. Prioritize growth over comfort.",
        }

        return f"""
User Profile:
- Preferred genres: {", ".join(self.genres)}
- Influences: {self.influences}
- Experience: {self.experience_level}
- Feedback style: {style_descriptions.get(self.feedback_style, self.feedback_style)}
""".strip()
```

### Full Tool Flow Example

```python
async def handle_chord_question(
    user_message: str,
    song: Song,
    user: User,
) -> str:
    """Complete flow: tool call → schema → data-to-text → LLM."""

    # 1. Agent decides to call tool (structured input)
    tool_input = AnalyzeChordsInput(
        chords=song.chord_progression,
        target_genre=user.preferences.genres[0],
    )

    # 2. Tool returns structured output
    analysis: ChordAnalysis = await analyze_chords(tool_input)

    # 3. Convert everything to readable text
    prompt = f"""
{PRODUCER_SYSTEM_PROMPT}

## Current Song
{song.to_prompt_text()}

## User Preferences
{user.preferences.to_prompt_text()}

## Chord Analysis (from tool)
{analysis.to_prompt_text()}

## User Question
{user_message}

Provide helpful guidance based on the analysis above:
"""

    # 4. LLM reasons with clean, readable context
    response = await llm.complete(prompt)

    return response
```

### Tool Definition with Schema

```python
from langchain.tools import StructuredTool

# Define tool with Pydantic schemas
analyze_chords_tool = StructuredTool.from_function(
    func=analyze_chords,
    name="analyze_chords",
    description="Analyze a chord progression for genre fit, tension, and suggestions",
    args_schema=AnalyzeChordsInput,
    return_direct=False,
)

# Agent sees this description and knows exactly what to pass
search_rhymes_tool = StructuredTool.from_function(
    func=search_rhymes,
    name="search_rhymes",
    description="Find rhyming words. Use rhyme_type='near' for subtle rhymes.",
    args_schema=SearchRhymesInput,
    return_direct=False,
)
```

---

## Advanced Agent Patterns

> Patterns derived from [Google's Real-World Agent Examples with Gemini](https://developers.googleblog.com/real-world-agent-examples-with-gemini-3/) and industry best practices.

### Self-Reflection and Correction

Agents should review their own output before returning to the user. This catches errors, improves quality, and enables self-correction.

**Pattern: Reflect-Then-Respond**

```python
async def critic_agent_with_reflection(song: Song, user: User) -> Critique:
    """Critic agent that reflects on its own feedback before delivering."""

    # 1. Generate initial critique
    initial_critique = await generate_critique(song, user)

    # 2. Self-reflect on the critique
    reflection = await llm.complete(f"""
Review this feedback you're about to give:

{initial_critique.to_text()}

Check for:
- Is it specific enough? (not just "make it better")
- Is it actionable? (user knows what to do)
- Does it match user's feedback style preference: {user.preferences.feedback_style}?
- Are you being too harsh or too soft?
- Did you miss any obvious issues?

Provide corrections or confirm it's ready.
""")

    # 3. Revise if needed
    if "REVISE:" in reflection:
        final_critique = await revise_critique(initial_critique, reflection)
    else:
        final_critique = initial_critique

    return final_critique
```

**When to Use:**
- Critic agent (feedback quality matters)
- Songwriter suggestions (creativity benefits from iteration)
- Any high-stakes output (career advice from Manager)

**When to Skip:**
- Simple tool calls (rhyme lookup)
- Low-latency requirements (real-time chat)
- Classification tasks (mood detection)

---

### Thought Signatures (State Management)

For extended, multi-step tasks, agents need to track their reasoning state. This prevents losing context and enables resumable workflows.

**Pattern: Agent State Tracking**

```python
from pydantic import BaseModel
from typing import Literal

class AgentThought(BaseModel):
    """Captures agent's reasoning state at a point in time."""
    goal: str                          # What we're trying to achieve
    approach: str                      # How we're approaching it
    confidence: float                  # 0-1, how confident in current path
    blockers: list[str]               # What's preventing progress
    next_actions: list[str]           # Planned next steps

class ExtendedTaskState(BaseModel):
    """Full state for multi-step tasks."""
    task_id: str
    task_type: Literal["song_review", "album_planning", "skill_coaching"]
    status: Literal["active", "paused", "completed", "blocked"]

    # Progress tracking
    steps_completed: list[str]
    current_step: str
    steps_remaining: list[str]

    # Reasoning trace
    thoughts: list[AgentThought]

    # Context
    song_id: str | None
    user_goals: str
    decisions_made: list[dict]

    # Timestamps
    started_at: datetime
    last_activity: datetime


async def coach_agent_with_state(
    user_message: str,
    state: ExtendedTaskState | None,
    user: User,
) -> tuple[str, ExtendedTaskState]:
    """Coach agent that maintains state across interactions."""

    # Initialize or resume state
    if state is None:
        state = ExtendedTaskState(
            task_id=str(uuid4()),
            task_type="skill_coaching",
            status="active",
            steps_completed=[],
            current_step="assess_current_skill",
            steps_remaining=["identify_gaps", "create_exercises", "track_progress"],
            thoughts=[],
            song_id=None,
            user_goals=user_message,
            decisions_made=[],
            started_at=datetime.now(),
            last_activity=datetime.now(),
        )

    # Record current thought
    thought = AgentThought(
        goal=f"Help user with: {state.user_goals}",
        approach=f"Currently on step: {state.current_step}",
        confidence=0.8,
        blockers=[],
        next_actions=state.steps_remaining[:2],
    )
    state.thoughts.append(thought)

    # Generate response with state context
    response = await llm.complete(f"""
{COACH_SYSTEM_PROMPT}

## Current Task State
Goal: {state.user_goals}
Progress: {len(state.steps_completed)}/{len(state.steps_completed) + len(state.steps_remaining) + 1} steps
Current step: {state.current_step}
Decisions so far: {state.decisions_made}

## User Message
{user_message}

Respond and indicate if current step is complete.
""")

    # Update state based on response
    if "[STEP_COMPLETE]" in response:
        state.steps_completed.append(state.current_step)
        if state.steps_remaining:
            state.current_step = state.steps_remaining.pop(0)
        else:
            state.status = "completed"

    state.last_activity = datetime.now()

    return response, state
```

**Use Cases:**
- Multi-session coaching programs
- Album planning (weeks of work)
- Complex song restructuring
- Goal tracking over time

---

### Memory Hierarchy (Letta Pattern)

Not all memories are equal. Implement a tiered memory system where agents actively manage what they remember.

```
┌─────────────────────────────────────────────────────────────┐
│                     CORE MEMORY                              │
│  Never forget: Identity, rules, user preferences             │
│  Examples: "User prefers encouraging feedback"               │
│            "User's genre is indie folk"                      │
└─────────────────────────────────────────────────────────────┘
                            ↑
                    (Always in prompt)
                            │
┌─────────────────────────────────────────────────────────────┐
│                    WORKING MEMORY                            │
│  Current task context: Active song, session goals            │
│  Examples: "Working on chorus for 'Empty Chair'"             │
│            "User wants to make it less literal"              │
└─────────────────────────────────────────────────────────────┘
                            ↑
                    (Retrieved per task)
                            │
┌─────────────────────────────────────────────────────────────┐
│                   ARCHIVAL MEMORY                            │
│  Long-term storage: Past songs, learnings, history           │
│  Examples: "Completed 12 songs in 2024"                      │
│            "Struggled with bridges, improved in October"     │
└─────────────────────────────────────────────────────────────┘
                            ↑
                    (Searched when relevant)
```

**Implementation:**

```python
class MemoryHierarchy:
    """Three-tier memory system for agents."""

    def __init__(self, user_id: UUID):
        self.user_id = user_id

    async def get_core_memory(self) -> str:
        """Always included in every prompt."""
        prefs = await get_user_preferences(self.user_id)
        return f"""
## Core Context (Always Remember)
- Feedback style: {prefs.feedback_style}
- Genres: {', '.join(prefs.genres)}
- Experience: {prefs.experience_level}
- Influences: {prefs.influences}
"""

    async def get_working_memory(self, song_id: UUID | None) -> str:
        """Current task context."""
        if not song_id:
            return ""

        song = await get_song(song_id)
        session = await get_current_session(self.user_id, song_id)

        return f"""
## Working Context (This Session)
- Song: "{song.title}"
- Current focus: {session.current_focus or "General"}
- Session goals: {session.goals or "None specified"}
- Recent decisions: {session.recent_decisions[-3:]}
"""

    async def search_archival_memory(self, query: str, limit: int = 5) -> str:
        """Search long-term memory for relevant context."""
        memories = await memory_search(
            query=query,
            user_id=self.user_id,
            limit=limit,
        )

        if not memories:
            return ""

        return f"""
## Relevant History
{chr(10).join(f"- {m.content}" for m in memories)}
"""

    async def build_context(
        self,
        query: str,
        song_id: UUID | None = None,
        include_archival: bool = True,
    ) -> str:
        """Build full context from all memory tiers."""
        parts = [await self.get_core_memory()]

        if song_id:
            parts.append(await self.get_working_memory(song_id))

        if include_archival:
            parts.append(await self.search_archival_memory(query))

        return "\n".join(parts)
```

**Key Insight:** Agents should *select* what context to include, not dump everything. This is why mem0 shows 90% lower token usage than naive approaches.

---

### Tool Ecosystem Design

> "Success depends on the ecosystem of tools that allow the model to interact with the world, not the model alone."

The model is commodity — your tools are the differentiator.

**Tool Categories for Songwriter App:**

| Category | Tools | Purpose |
|----------|-------|---------|
| **Analysis** | `analyze_lyrics`, `analyze_meter`, `analyze_chords` | Understand current state |
| **Search** | `search_rhymes`, `find_synonyms`, `find_similar_songs` | Expand options |
| **Context** | `get_song_context`, `get_user_history`, `get_genre_conventions` | Ground in reality |
| **Action** | `save_revision`, `add_note`, `set_goal` | Make changes |
| **External** | `web_search`, `get_reference_track` | Bring in outside info |

**Tool Design Principles:**

```python
# 1. Single responsibility
# BAD: One tool does everything
async def song_helper(action: str, song_id: str, **kwargs):
    if action == "analyze": ...
    elif action == "rhyme": ...
    elif action == "save": ...

# GOOD: Focused tools
async def analyze_lyrics(song_id: str) -> LyricAnalysis: ...
async def search_rhymes(word: str, type: RhymeType) -> list[str]: ...
async def save_revision(song_id: str, content: str) -> Revision: ...


# 2. Rich return types (agent can reason about results)
# BAD: Returns unstructured string
async def analyze_chords(chords: list[str]) -> str:
    return f"The progression {chords} is common in pop music"

# GOOD: Returns structured data
async def analyze_chords(chords: list[str]) -> ChordAnalysis:
    return ChordAnalysis(
        chords=chords,
        key="C major",
        genre_fit=["pop", "folk", "indie"],
        tension_level=3,
        suggestions=["Try Fmaj7 instead of F for color"],
    )


# 3. Composable (tools can build on each other)
async def comprehensive_analysis(song_id: str) -> FullAnalysis:
    song = await get_song_context(song_id)
    lyrics = await analyze_lyrics(song_id)
    chords = await analyze_chords(song.chord_progression)
    structure = await evaluate_structure(song_id)

    return FullAnalysis(
        song=song,
        lyrics=lyrics,
        chords=chords,
        structure=structure,
    )
```

---

### Multi-Agent Composition (ADK Pattern)

Compose specialized agents into unified tools that work together with self-reflection.

```python
class ComposedSongReviewAgent:
    """
    Combines Critic + Producer + Songwriter into a unified review experience.
    Uses self-reflection to ensure coherent output.
    """

    def __init__(self, user: User):
        self.user = user
        self.critic = CriticAgent(user)
        self.producer = ProducerAgent(user)
        self.songwriter = SongwriterAgent(user)

    async def full_review(self, song: Song) -> ComprehensiveReview:
        # 1. Gather perspectives in parallel
        critic_review, producer_review = await asyncio.gather(
            self.critic.analyze(song),
            self.producer.analyze(song),
        )

        # 2. Synthesize into unified feedback
        synthesis = await self._synthesize(critic_review, producer_review, song)

        # 3. Self-reflect on the combined review
        reflection = await self._reflect(synthesis)

        # 4. Generate actionable suggestions via Songwriter
        suggestions = await self.songwriter.generate_improvements(
            song=song,
            feedback=synthesis,
            reflection=reflection,
        )

        # 5. Package final review
        return ComprehensiveReview(
            lyric_feedback=critic_review,
            musical_feedback=producer_review,
            synthesis=synthesis,
            suggestions=suggestions,
            priority_order=self._prioritize(suggestions),
        )

    async def _synthesize(
        self,
        critic: CriticReview,
        producer: ProducerReview,
        song: Song,
    ) -> str:
        return await llm.complete(f"""
Synthesize these two reviews into coherent feedback:

## Lyric Review (Critic)
{critic.to_text()}

## Musical Review (Producer)
{producer.to_text()}

Create a unified narrative that:
1. Identifies where lyric and music feedback align
2. Notes any tensions between the two
3. Prioritizes the most impactful changes
""")

    async def _reflect(self, synthesis: str) -> str:
        return await llm.complete(f"""
Review this feedback synthesis before presenting to the user:

{synthesis}

Check:
- Is it overwhelming? (too many suggestions at once)
- Is it actionable?
- Does it respect the user's creative vision?
- Are the priorities correct?

Suggest any adjustments.
""")
```

---

## ReAct Loop for Creative Iteration

Creative work is inherently iterative. The **Reason-Act-Observe** pattern fits perfectly:

```python
class CreativeReActLoop:
    """
    Adapting the ReAct pattern for songwriting.
    Each iteration refines the creative output.
    """

    async def process(
        self,
        user_request: str,
        context: CreativeContext,
        max_iterations: int = 5,
    ) -> CreativeOutput:

        for iteration in range(max_iterations):
            # REASON: Analyze current state and plan next action
            reasoning = await self.reason(
                request=user_request,
                current_output=context.current_draft,
                feedback=context.last_feedback,
                constraints=context.creative_constraints,
            )

            # ACT: Execute the planned creative action
            if reasoning.action_type == "delegate_to_agent":
                result = await self.delegate_to_specialist(
                    agent=reasoning.target_agent,
                    task=reasoning.task_description,
                    context=context,
                )
            elif reasoning.action_type == "synthesize":
                result = await self.synthesize_outputs(context.agent_outputs)
            elif reasoning.action_type == "refine":
                result = await self.refine_output(
                    current=context.current_draft,
                    refinement=reasoning.refinement_instructions,
                )

            # OBSERVE: Evaluate the result
            observation = await self.observe(
                result=result,
                original_request=user_request,
                quality_criteria=context.quality_criteria,
            )

            # Check if we've achieved the goal
            if observation.goal_achieved:
                return result

            # Update context for next iteration
            context.update(result, observation)

        return context.best_output
```

**When to Iterate:**
- User says "make it better" (subjective goal)
- Complex multi-part requests
- Quality threshold not met

**When to Stop:**
- User explicitly approves
- Quality criteria satisfied
- Max iterations reached
- User requests different direction

---

## Agent Dependencies

Agents have natural dependencies based on the creative workflow:

```python
from dataclasses import dataclass
from typing import List

@dataclass
class AgentCapability:
    """Defines what an agent can do and what it needs."""
    role: str
    description: str
    can_handle: List[str]          # Intent patterns
    requires_input_from: List[str]  # Dependencies
    outputs: List[str]              # What this agent produces


AGENT_CAPABILITIES = {
    "theme": AgentCapability(
        role="theme_architect",
        description="Develops overarching themes, emotional arcs, and imagery",
        can_handle=["concept", "theme", "mood", "story", "meaning"],
        requires_input_from=[],  # Can work independently
        outputs=["theme_document", "imagery_palette", "emotional_arc"],
    ),

    "lyrics": AgentCapability(
        role="lyricist",
        description="Writes lyrics with attention to meter, rhyme, and meaning",
        can_handle=["lyrics", "words", "verses", "chorus", "rhyme"],
        requires_input_from=["theme"],  # Needs theme first
        outputs=["lyrics", "rhyme_scheme", "syllable_map"],
    ),

    "melody": AgentCapability(
        role="melodist",
        description="Creates melodic contours that match lyrics and emotion",
        can_handle=["melody", "tune", "hook", "vocal line"],
        requires_input_from=["lyrics", "theme"],  # Needs lyrics and theme
        outputs=["melody_contour", "pitch_sequence", "rhythm_pattern"],
    ),

    "harmony": AgentCapability(
        role="harmonist",
        description="Develops chord progressions and harmonic structure",
        can_handle=["chords", "harmony", "key", "progression"],
        requires_input_from=["melody", "theme"],  # Can parallel with lyrics
        outputs=["chord_progression", "key_signature", "harmonic_analysis"],
    ),

    "arrangement": AgentCapability(
        role="arranger",
        description="Structures the song and plans instrumentation",
        can_handle=["structure", "arrangement", "sections", "dynamics"],
        requires_input_from=["lyrics", "harmony"],  # Needs content first
        outputs=["song_structure", "section_order", "dynamics_map"],
    ),
}
```

### Dependency Graph

```
                    ┌─────────┐
                    │  Theme  │ ← Independent, starts first
                    └────┬────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
       ┌─────────┐ ┌─────────┐ ┌─────────┐
       │ Lyrics  │ │ Harmony │ │  Mood   │  ← Can run in parallel
       └────┬────┘ └────┬────┘ └─────────┘
            │           │
            └─────┬─────┘
                  ▼
            ┌─────────┐
            │ Melody  │ ← Needs lyrics + chords
            └────┬────┘
                 │
                 ▼
          ┌───────────┐
          │Arrangement│ ← Needs everything
          └───────────┘
```

---

## Agent Communication Protocol

Structured message passing between agents ensures reliable handoffs:

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AgentMessage:
    """
    Inter-agent communication protocol.
    Enables reliable handoffs with full context.
    """
    from_agent: str
    to_agent: str
    message_type: str  # "request", "response", "feedback", "handoff"

    # The creative artifact being passed
    payload: dict  # lyrics, chords, melody data, etc.

    # Context for the receiving agent
    context: dict  # What the sender wants, constraints, etc.

    # Provenance tracking
    reasoning_trace: List[str]  # Why this was created/modified
    confidence: float  # How confident the sender is (0-1)

    # For iterative refinement
    iteration: int
    feedback_from_previous: Optional[str] = None


# Example handoff
handoff = AgentMessage(
    from_agent="critic",
    to_agent="songwriter",
    message_type="handoff",
    payload={
        "analysis": "Verse 2 lacks specific imagery",
        "weak_lines": [3, 4],
        "suggestions": ["Add sensory details", "Show don't tell"],
    },
    context={
        "user_goal": "Make verse more powerful",
        "preserve": ["The opening line is strong"],
    },
    reasoning_trace=[
        "User said verse feels weak",
        "Analyzed: lines 3-4 are abstract",
        "Recommendation: add concrete imagery",
    ],
    confidence=0.85,
    iteration=1,
)
```

---

## Creative Guardrails

Validate creative outputs before returning to user:

```python
class CreativeGuardrails:
    """
    Ensure creative outputs meet quality and ethical standards.
    """

    def __init__(self):
        self.plagiarism_detector = PlagiarismChecker()
        self.music_theory_validator = TheoryValidator()
        self.content_filter = ContentModerator()
        self.prosody_checker = ProsodyChecker()

    async def validate(self, output: CreativeOutput) -> ValidationResult:
        checks = []

        # 1. Originality check
        if output.lyrics:
            plagiarism = await self.plagiarism_detector.check(output.lyrics)
            checks.append(GuardrailCheck(
                name="originality",
                passed=plagiarism.similarity_score < 0.3,
                details=f"Highest match: {plagiarism.top_match}",
                severity="blocking" if plagiarism.similarity_score > 0.5 else "warning",
            ))

        # 2. Music theory validation
        if output.chords and output.melody:
            theory_check = self.music_theory_validator.validate(
                chords=output.chords,
                melody=output.melody,
                key=output.key,
            )
            checks.append(GuardrailCheck(
                name="harmonic_coherence",
                passed=theory_check.is_valid,
                details=theory_check.issues,
                severity="warning",  # Theory "rules" can be broken
            ))

        # 3. Prosody check (lyrics + melody alignment)
        if output.lyrics and output.melody:
            prosody = self.prosody_checker.analyze(output.lyrics, output.melody)
            checks.append(GuardrailCheck(
                name="prosody",
                passed=prosody.alignment_score > 0.7,
                details=prosody.problem_spots,
                severity="warning",
            ))

        # 4. Content appropriateness
        if output.lyrics:
            content = await self.content_filter.analyze(output.lyrics)
            checks.append(GuardrailCheck(
                name="content_policy",
                passed=content.is_appropriate,
                details=content.flags,
                severity="blocking" if content.has_prohibited else "info",
            ))

        # 5. Cliché detection
        if output.lyrics:
            cliches = self.detect_cliches(output.lyrics)
            checks.append(GuardrailCheck(
                name="originality_style",
                passed=len(cliches) < 3,
                details=f"Found clichés: {cliches}",
                severity="info",  # Inform, don't block
            ))

        return ValidationResult(
            passed=all(c.passed for c in checks if c.severity == "blocking"),
            checks=checks,
            blocking_issues=[c for c in checks if not c.passed and c.severity == "blocking"],
            warnings=[c for c in checks if not c.passed and c.severity == "warning"],
        )
```

### When Guardrails Fire

| Check | Blocking | Warning | Info |
|-------|----------|---------|------|
| Plagiarism > 50% | ✓ | | |
| Plagiarism 30-50% | | ✓ | |
| Theory violations | | ✓ | |
| Prosody misalignment | | ✓ | |
| Prohibited content | ✓ | | |
| Clichés detected | | | ✓ |

---

## Orchestration Architecture

### LangGraph State Machine

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

class ConversationState(TypedDict):
    messages: list[Message]
    current_song: Song | None
    active_agent: str
    user_intent: str
    pending_actions: list[Action]
    context: dict

# Define the workflow
workflow = StateGraph(ConversationState)

# Add agent nodes
workflow.add_node("router", route_to_agent)
workflow.add_node("songwriter", songwriter_agent)
workflow.add_node("producer", producer_agent)
workflow.add_node("critic", critic_agent)
workflow.add_node("coach", coach_agent)
workflow.add_node("manager", manager_agent)
workflow.add_node("researcher", researcher_agent)

# Router decides which agent handles the request
workflow.add_conditional_edges(
    "router",
    determine_agent,
    {
        "songwriter": "songwriter",
        "producer": "producer",
        "critic": "critic",
        "coach": "coach",
        "manager": "manager",
        "researcher": "researcher",
    }
)

# Agents can hand off to each other
workflow.add_conditional_edges(
    "songwriter",
    check_handoff,
    {
        "producer": "producer",      # "What chords work here?"
        "critic": "critic",          # "Is this verse good?"
        "continue": "songwriter",    # Keep working
        "done": END,
    }
)
```

### Routing Logic

```python
async def route_to_agent(state: ConversationState) -> str:
    """Determine which agent should handle the user's request."""

    user_message = state["messages"][-1].content

    # Use LLM to classify intent
    classification = await llm.complete(
        f"""Classify this user request into one category:
        - songwriter: lyrics, themes, hooks, rhymes, structure
        - producer: chords, arrangement, sound, production, genre
        - critic: feedback, review, evaluation, what's wrong
        - coach: learning, exercises, how to improve, techniques
        - manager: releases, goals, planning, career, schedule
        - researcher: find info, examples, trends, context

        User request: {user_message}

        Category:"""
    )

    return classification.strip().lower()
```

### Agent Handoffs

Agents can transfer to each other mid-conversation:

```python
async def songwriter_agent(state: ConversationState) -> ConversationState:
    """Songwriter agent with handoff capability."""

    response = await llm.complete(
        messages=state["messages"],
        tools=songwriter_tools,
        system=SONGWRITER_SYSTEM_PROMPT,
    )

    # Check if agent wants to hand off
    if "HANDOFF:producer" in response.metadata:
        state["pending_handoff"] = "producer"
        state["handoff_context"] = "Need chord suggestions for this section"

    state["messages"].append(response)
    return state
```

### Example Multi-Agent Flow

```
User: "I'm writing a breakup song but it sounds too whiny.
       Can you help me make it more powerful?"

┌─────────────────────────────────────────────────────────────┐
│ 1. ROUTER                                                   │
│    → Detects: needs feedback (critic) + rewrite (songwriter)│
│    → Routes to: Critic first                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CRITIC AGENT                                             │
│    → Calls: analyze_lyrics(current_song)                    │
│    → Identifies: passive voice, self-pity framing           │
│    → Feedback: "The issue is perspective - you're the       │
│      victim in every line. Powerful breakup songs often     │
│      show strength or transformation."                      │
│    → Handoff: songwriter (with specific guidance)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. SONGWRITER AGENT                                         │
│    → Receives: critic's analysis                            │
│    → Calls: find_similar_songs("empowering breakup")        │
│    → References: "Since U Been Gone", "Survivor"            │
│    → Rewrites: chorus with active voice, strength framing   │
│    → Offers: 3 alternative versions                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. RESPONSE TO USER                                         │
│    "Your chorus 'I can't stop crying over you' puts you in  │
│    a passive, powerless position. Try flipping it:          │
│                                                             │
│    Option A: 'I finally stopped crying over you'            │
│    Option B: 'These tears? They're not for you anymore'     │
│    Option C: 'I'm done letting you make me cry'             │
│                                                             │
│    Each shows agency and transformation - much more         │
│    powerful than being stuck in the pain."                  │
└─────────────────────────────────────────────────────────────┘
```

---

## State Management

### Conversation Memory

```python
class AgentMemory:
    """Manages context across agent interactions."""

    def __init__(self, user_id: UUID, song_id: UUID | None):
        self.user_id = user_id
        self.song_id = song_id
        self.messages: list[Message] = []
        self.agent_context: dict[str, dict] = {}
        self.decisions: list[Decision] = []

    async def load(self):
        """Load from database."""
        self.messages = await get_chat_history(self.user_id, self.song_id)
        self.agent_context = await get_agent_context(self.user_id)

    async def save(self):
        """Persist to database."""
        await save_chat_history(self.user_id, self.song_id, self.messages)
        await save_agent_context(self.user_id, self.agent_context)

    def get_agent_memory(self, agent: str) -> dict:
        """Get context specific to an agent."""
        return self.agent_context.get(agent, {})

    def update_agent_memory(self, agent: str, data: dict):
        """Update agent-specific context."""
        if agent not in self.agent_context:
            self.agent_context[agent] = {}
        self.agent_context[agent].update(data)
```

### Song Context

```python
class SongContext:
    """Full context about the current song for agents."""

    song: Song
    sections: list[Section]
    version_history: list[Version]
    notes: list[Note]
    audio_files: list[AudioFile]
    collaborators: list[User]

    # Computed
    word_count: int
    section_count: int
    has_chorus: bool
    has_bridge: bool
    estimated_duration: float

    # User's intentions
    target_genre: str
    target_mood: str
    reference_songs: list[str]
    user_goals: str
```

---

## Agent Prompts

### Songwriter Partner System Prompt

```python
SONGWRITER_SYSTEM_PROMPT = """You are a skilled songwriter and creative partner.

Your role:
- Collaborate on lyrics, not write them alone
- Respect the user's voice and vision
- Offer options, not mandates
- Push creative boundaries gently
- Remember context from earlier in the session

Your style:
- Speak as a fellow creative, not an authority
- Use "we" language: "What if we tried..."
- Celebrate good ideas before suggesting changes
- Be specific in suggestions (not "make it better" but "try a harder consonant sound")

Tools available:
{tools}

Current song context:
{song_context}

User preferences:
{user_preferences}
"""
```

### Agent Handoff Protocol

```python
HANDOFF_INSTRUCTIONS = """
If the user's request requires expertise outside your domain,
you can hand off to another agent.

To hand off, end your response with:
HANDOFF:<agent_name>
CONTEXT:<brief context for the other agent>

Available agents:
- songwriter: lyrics, themes, structure
- producer: chords, arrangement, sound
- critic: feedback, evaluation
- coach: learning, exercises
- manager: career, releases
- researcher: information, trends

Example:
"That's a great question about chord voicings! Let me bring in
our producer perspective on this.

HANDOFF:producer
CONTEXT:User wants to know about jazzy chord voicings for verse"
"""
```

---

## Database Schema

```sql
-- Agent conversation history
CREATE TABLE agent_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    song_id UUID REFERENCES songs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual messages with agent attribution
CREATE TABLE agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES agent_conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    agent VARCHAR(50), -- 'songwriter', 'producer', etc.
    content TEXT NOT NULL,
    tool_calls JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent-specific memory per user
CREATE TABLE agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent VARCHAR(50) NOT NULL,
    memory JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, agent)
);

-- Learning/coaching progress
CREATE TABLE user_skill_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    skill VARCHAR(100) NOT NULL,
    level INTEGER DEFAULT 0,
    exercises_completed INTEGER DEFAULT 0,
    last_practiced TIMESTAMPTZ,
    notes JSONB,
    UNIQUE(user_id, skill)
);

-- Career goals and milestones
CREATE TABLE user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    target_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    progress INTEGER DEFAULT 0,
    milestones JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Implementation Phases

### Phase 1: Enhanced Single Agent
- Add tool-use to existing chat
- Implement song context injection
- Add structured outputs

### Phase 2: Specialized Agents
- Split into Songwriter + Critic
- Add Producer agent
- Implement basic routing

### Phase 3: Agent Orchestration
- Add LangGraph for workflow management
- Implement handoffs between agents
- Add conversation memory

### Phase 4: Coach & Manager
- Learning path tracking
- Goal setting and milestones
- Release planning features

### Phase 5: Full Integration
- Seamless multi-agent conversations
- Cross-agent memory sharing
- Proactive agent suggestions

---

## API Design

```python
# Chat with automatic agent routing
@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: CurrentUser,
) -> ChatResponse:
    """
    Send a message and get a response from the appropriate agent(s).
    """
    orchestrator = AgentOrchestrator(user)
    response = await orchestrator.process(request.message, request.song_id)
    return response

# Direct agent access
@router.post("/agents/{agent}/chat")
async def chat_with_agent(
    agent: Literal["songwriter", "producer", "critic", "coach", "manager"],
    request: ChatRequest,
    user: CurrentUser,
) -> ChatResponse:
    """
    Chat directly with a specific agent.
    """
    agent_instance = get_agent(agent, user)
    response = await agent_instance.process(request.message, request.song_id)
    return response

# Get agent suggestions (proactive)
@router.get("/songs/{song_id}/suggestions")
async def get_suggestions(
    song_id: UUID,
    user: CurrentUser,
) -> list[AgentSuggestion]:
    """
    Get proactive suggestions from all agents about the current song.
    """
    suggestions = await gather_agent_suggestions(song_id, user)
    return suggestions
```

---

## Frontend Concepts

### Agent Avatars/Personas

Each agent could have a distinct visual identity:

```typescript
const AGENTS = {
  songwriter: {
    name: "Alex",
    role: "Songwriter Partner",
    avatar: "/agents/songwriter.png",
    color: "#6366f1", // indigo
  },
  producer: {
    name: "Jordan",
    role: "Producer",
    avatar: "/agents/producer.png",
    color: "#8b5cf6", // violet
  },
  critic: {
    name: "Sam",
    role: "Critic",
    avatar: "/agents/critic.png",
    color: "#ec4899", // pink
  },
  // ...
};
```

### Agent Switching UI

```
┌─────────────────────────────────────────────────────────────┐
│  Chat with your creative team                               │
├─────────────────────────────────────────────────────────────┤
│ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                    │
│ │ 🎸  │ │ 🎹  │ │ 📝  │ │ 🎓  │ │ 📊  │    ← Agent tabs    │
│ │Alex │ │Jord │ │ Sam │ │Coach│ │ Mgr │                    │
│ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🎸 Alex (Songwriter):                                      │
│  "I love the imagery in your chorus! The 'paper walls'      │
│   metaphor is strong. For verse 2, what if we explored      │
│   the moment right before everything fell apart?"           │
│                                                             │
│  You:                                                       │
│  "Yeah, I want to show the tension building"                │
│                                                             │
│  🎸 Alex:                                                   │
│  "Perfect. Let me get Jordan's take on building that        │
│   tension musically too..."                                 │
│                                                             │
│  🎹 Jordan (Producer):                                      │
│  "For building tension, try: (1) reduce the chord rhythm    │
│   in V2, (2) add a suspended chord before the chorus,       │
│   (3) strip back instruments then explode into chorus"      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [Type your message...]                            [Send]   │
└─────────────────────────────────────────────────────────────┘
```

---

## Success Metrics

- **Engagement:** Time spent in agent conversations
- **Completion:** Songs finished with agent assistance
- **Learning:** Skills improved (coach tracking)
- **Satisfaction:** Agent helpfulness ratings
- **Retention:** Users returning to work with agents

---

## Technical Considerations

### Cost Management

Multiple agents = more LLM calls. Mitigate with:

```python
# Use cheaper models for routing
ROUTING_MODEL = "gpt-4o-mini"  # Fast, cheap

# Use capable models for agents
AGENT_MODEL = "claude-sonnet-4"  # Quality responses

# Cache common patterns
@cache(ttl=3600)
async def get_genre_conventions(genre: str) -> dict:
    ...
```

### Latency

Agent handoffs add latency. Optimize with:

- Parallel tool calls where possible
- Streaming responses
- Predictive loading of likely next agents

### Context Limits

Long conversations hit token limits:

```python
async def compress_history(messages: list[Message]) -> list[Message]:
    """Summarize older messages to fit context window."""
    if len(messages) < 20:
        return messages

    old_messages = messages[:-10]
    recent_messages = messages[-10:]

    summary = await llm.complete(
        f"Summarize this conversation: {old_messages}"
    )

    return [Message(role="system", content=f"Previous context: {summary}")] + recent_messages
```

---

## Getting Started: Minimal Implementation

A working starting point you can build from:

```python
# songwriting_agents.py
from anthropic import Anthropic
from dataclasses import dataclass
from typing import Dict
import asyncio


@dataclass
class SongContext:
    """Accumulated creative work for a song."""
    genre: str
    mood: str
    theme_description: str
    key: str | None = None
    tempo: int | None = None
    structure: str = "verse-chorus-verse-chorus-bridge-chorus"

    # Accumulated outputs
    theme_doc: str | None = None
    lyrics: Dict[str, str] | None = None  # section -> lyrics
    chords: Dict[str, list[str]] | None = None


class SongwritingAgent:
    """Base class for specialist agents."""

    def __init__(self, role: str, system_prompt: str):
        self.role = role
        self.system_prompt = system_prompt
        self.client = Anthropic()

    async def process(self, task: str, context: SongContext) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=self.system_prompt,
            messages=[{
                "role": "user",
                "content": f"""
Context:
- Genre: {context.genre}
- Mood: {context.mood}
- Theme: {context.theme_description}
- Key: {context.key or 'Not yet determined'}
- Structure: {context.structure}

Previous work:
{self._format_previous_work(context)}

Task: {task}
"""
            }]
        )
        return response.content[0].text

    def _format_previous_work(self, context: SongContext) -> str:
        parts = []
        if context.theme_doc:
            parts.append(f"Theme Document:\n{context.theme_doc}")
        if context.lyrics:
            parts.append(f"Lyrics:\n{context.lyrics}")
        if context.chords:
            parts.append(f"Chords:\n{context.chords}")
        return "\n\n".join(parts) if parts else "None yet"


class ThemeAgent(SongwritingAgent):
    def __init__(self):
        super().__init__(
            role="theme_architect",
            system_prompt="""You are a Theme Architect for songwriting.
Your job is to develop the conceptual foundation of a song:
- Core emotional arc (where does the song start and end emotionally?)
- Key imagery and metaphors to use
- The "world" of the song (setting, perspective, voice)
- What makes this song feel authentic and specific

Output a theme document that other agents can use as their north star.
Be specific and evocative, not generic."""
        )


class LyricistAgent(SongwritingAgent):
    def __init__(self):
        super().__init__(
            role="lyricist",
            system_prompt="""You are a master Lyricist.
Given a theme document and song structure, write lyrics that:
- Honor the emotional arc from the theme
- Use the imagery and metaphors established
- Have strong meter and natural rhythm for singing
- Include internal rhymes and consonance, not just end rhymes
- Avoid clichés - find fresh ways to express feelings

Format output clearly by section (Verse 1, Chorus, etc.)
Include syllable counts for each line."""
        )


class HarmonyAgent(SongwritingAgent):
    def __init__(self):
        super().__init__(
            role="harmonist",
            system_prompt="""You are a Harmony specialist and chord progression expert.
Given a theme, mood, and genre, develop chord progressions that:
- Support the emotional arc (tension, release, resolution)
- Fit the genre conventions while being interesting
- Work well with the vocal melody range

Output chord progressions for each section with:
- Roman numeral analysis
- Specific chord names (e.g., Cmaj7, Am7)
- Notes on feel/strumming patterns"""
        )


class SongOrchestrator:
    """Central coordinator for multi-agent collaboration."""

    def __init__(self):
        self.agents = {
            "theme": ThemeAgent(),
            "lyrics": LyricistAgent(),
            "harmony": HarmonyAgent(),
        }

    async def compose(self, request: str, genre: str, mood: str) -> Dict:
        context = SongContext(
            genre=genre,
            mood=mood,
            theme_description=request,
        )

        # Phase 1: Develop theme (independent)
        print("Developing theme...")
        context.theme_doc = await self.agents["theme"].process(
            f"Develop a theme for: {request}",
            context,
        )

        # Phase 2: Lyrics and chords in parallel (both depend on theme)
        print("Writing lyrics and chords...")
        lyrics_task = self.agents["lyrics"].process(
            "Write complete lyrics following the theme document",
            context,
        )
        harmony_task = self.agents["harmony"].process(
            "Develop chord progressions for each section",
            context,
        )

        lyrics_result, harmony_result = await asyncio.gather(
            lyrics_task, harmony_task
        )

        context.lyrics = lyrics_result
        context.chords = harmony_result

        return {
            "theme": context.theme_doc,
            "lyrics": context.lyrics,
            "chords": context.chords,
        }


# Usage
async def main():
    orchestrator = SongOrchestrator()

    song = await orchestrator.compose(
        request="A bittersweet song about watching your kids grow up",
        genre="indie folk",
        mood="nostalgic, tender, with underlying hope",
    )

    print("\n" + "=" * 60)
    print("COMPLETED SONG")
    print("=" * 60)
    for section, content in song.items():
        print(f"\n## {section.upper()}\n{content}")


if __name__ == "__main__":
    asyncio.run(main())
```

### Running the Example

```bash
# Install dependency
uv add anthropic

# Set API key
export ANTHROPIC_API_KEY=your-key

# Run
python songwriting_agents.py
```

### Next Steps from Here

1. **Add Style Library retrieval** - Ground agents in user's past work
2. **Add guardrails** - Validate outputs before returning
3. **Add more agents** - Critic, Coach, Producer
4. **Add handoffs** - Let agents transfer to each other
5. **Add persistence** - Save conversations and state
6. **Integrate with app** - Wire into FastAPI routes

---

## Agentforce Concept Mapping

For those familiar with Salesforce Agentforce architecture:

| Agentforce Concept | Songwriter App Equivalent |
|-------------------|---------------------------|
| Atlas Reasoning Engine | `SongOrchestrator` with ReAct loop |
| Topics | Creative domains (lyrics, melody, chords) |
| Actions | Tools (rhyme lookup, chord analysis) |
| Instructions | Agent system prompts |
| Data Cloud + RAG | Style Library (user's songs + music theory) |
| Multi-agent A2A | `AgentMessage` protocol |
| Guardrails | `CreativeGuardrails` (plagiarism, theory, prosody) |
| Einstein Trust Layer | Content moderation |
| Flex model routing | Use Claude for lyrics, cheaper models for lookups |

---

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [ReAct: Reasoning and Acting in LLMs](https://arxiv.org/abs/2210.03629)
- [Multi-Agent Collaboration Patterns](https://www.anthropic.com/research/building-effective-agents)
- [Tool Use Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Real-World Agent Examples with Gemini](https://developers.googleblog.com/real-world-agent-examples-with-gemini-3/) — ADK, Letta, mem0 patterns
- [State of AI Coding 2025](https://www.greptile.com/state-of-ai-coding-2025) — mem0 market share, model benchmarks
