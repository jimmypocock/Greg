# Mem0 Memory Layer Integration

> **Status:** Future Consideration (Phase 3+)
> **Priority:** Medium (after MVP validation)
> **Market Position:** 59% market share in AI memory infrastructure
> **Website:** [mem0.ai](https://mem0.ai)

## Overview

Mem0 is an intelligent memory layer for AI applications that enables persistent, personalized memory across conversations. Instead of treating each interaction as isolated, mem0 allows AI agents to "remember" user preferences, past decisions, and context — creating more natural, continuous experiences.

```
Without Memory:
User: "I like folk music"
[Next session]
User: "Suggest a chord progression"
AI: [No context about folk preference]

With Mem0:
User: "I like folk music"
[Memory stored: user prefers folk]
[Next session]
User: "Suggest a chord progression"
AI: [Retrieves folk preference] → Suggests folk-appropriate progressions
```

## Why Mem0 vs Simple Database Preferences

| Approach | Best For | Limitations |
|----------|----------|-------------|
| **Database Preferences** | Explicit settings (genre, feedback style) | User must manually configure |
| **Mem0** | Implicit learning from conversations | Requires more infrastructure |

### When to Use Database Preferences (Current MVP)

```python
# User explicitly sets preferences
class UserPreferences(BaseModel):
    genres: list[str]  # ["folk", "indie"]
    feedback_style: str  # "encouraging"
    experience_level: str  # "intermediate"
```

- User controls what's stored
- Simple to implement
- Predictable behavior
- Good for MVP

### When to Use Mem0 (Future)

```python
# System learns from conversations
User: "I always struggle with bridge sections"
→ Mem0 stores: "User finds bridges challenging"

User: "I love how Bon Iver uses falsetto"
→ Mem0 stores: "User influenced by Bon Iver, appreciates falsetto"

# Later, unprompted:
AI: "Since bridges are tricky for you, let's try a simpler
     approach. And given your Bon Iver influence, consider
     a falsetto moment in the pre-chorus..."
```

- System learns implicitly
- Richer personalization
- More "magical" UX
- Better for mature product

## Architecture

### Memory Hierarchy (Letta Pattern)

> Pattern derived from [Letta's memory hierarchy](https://developers.googleblog.com/real-world-agent-examples-with-gemini-3/) which enables agents to "manage their own context window effectively and run indefinitely without forgetting core instructions."

Not all memories are equal. Implement a tiered system where agents actively manage what they remember:

```
┌─────────────────────────────────────────────────────────────┐
│                     CORE MEMORY                              │
│  Never forget: Identity, rules, user preferences             │
│  Examples: "User prefers encouraging feedback"               │
│  → ALWAYS in prompt (small, essential)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    WORKING MEMORY                            │
│  Current task: Active song, session goals, recent decisions  │
│  Examples: "Working on chorus for 'Empty Chair'"             │
│  → Retrieved per task (moderate, task-specific)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   ARCHIVAL MEMORY                            │
│  Long-term: Past songs, learnings, growth over time          │
│  Examples: "Struggled with bridges, improved in October"     │
│  → Searched when relevant (large, semantic search)           │
└─────────────────────────────────────────────────────────────┘
```

**Key Insight:** Agents should *select* what context to include, not dump everything. This is why mem0 shows 90% lower token usage than naive full-context approaches.

### Memory Types

| Type | Scope | Use Case | Hierarchy Level |
|------|-------|----------|-----------------|
| **User Memory** | Persists across all sessions | Preferences, style, history | Core + Archival |
| **Agent Memory** | Specific to an agent | Agent-specific context | Working + Archival |
| **Session Memory** | Single conversation | Current song, immediate context | Working |

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interaction                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Mem0 Memory Layer                        │
├─────────────────────────────────────────────────────────────┤
│  1. SEARCH: Find relevant memories for current context      │
│  2. ENHANCE: Add memories to LLM prompt                     │
│  3. RESPOND: Generate contextual response                   │
│  4. EXTRACT: Identify new facts from conversation           │
│  5. STORE: Save new memories for future                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Vector Database                           │
│              (Embeddings for semantic search)                │
└─────────────────────────────────────────────────────────────┘
```

## Performance Benefits

From mem0's benchmarks:

| Metric | Improvement |
|--------|-------------|
| Accuracy | +26% over OpenAI Memory (LOCOMO benchmark) |
| Response Speed | 91% faster |
| Token Usage | 90% lower vs full-context approaches |

The key insight: **strategic memory retrieval beats naive long-context**. Instead of stuffing entire conversation history into prompts, mem0 retrieves only relevant memories.

## Implementation

### Installation

```bash
pip install mem0ai
```

### Option 1: Hosted Platform (Recommended for Start)

```python
from mem0 import MemoryClient

client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# Add memory from conversation
messages = [
    {"role": "user", "content": "I've been writing songs for 5 years"},
    {"role": "assistant", "content": "Great! That's solid experience."}
]
client.add(messages, user_id=str(user.id))

# Search relevant memories
memories = client.search(
    "What's the user's experience level?",
    filters={"user_id": str(user.id)}
)
# Returns: [{"memory": "Has been writing songs for 5 years", ...}]
```

### Option 2: Self-Hosted (Full Control)

```python
from mem0 import Memory

# Configure with your own infrastructure
config = {
    "llm": {
        "provider": "anthropic",
        "config": {
            "model": "claude-sonnet-4-20250514",
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
        }
    },
    "vector_store": {
        "provider": "pgvector",  # Use existing PostgreSQL
        "config": {
            "connection_string": os.getenv("DATABASE_URL"),
            "collection_name": "memories",
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": os.getenv("OPENAI_API_KEY"),
        }
    }
}

memory = Memory.from_config(config)
```

## Integration with Multi-Agent Architecture

### Per-Agent Memory

Each agent can have its own memory context:

```python
# Songwriter agent remembers creative preferences
songwriter_memory = client.search(
    query="user's songwriting style and influences",
    filters={"user_id": user_id, "agent_id": "songwriter"}
)

# Critic agent remembers feedback history
critic_memory = client.search(
    query="past feedback and user's growth areas",
    filters={"user_id": user_id, "agent_id": "critic"}
)

# Coach agent remembers learning progress
coach_memory = client.search(
    query="skills practiced and areas to improve",
    filters={"user_id": user_id, "agent_id": "coach"}
)
```

### Memory-Enhanced Agent Prompts

```python
async def songwriter_agent(user_message: str, song: Song, user: User) -> str:
    # 1. Retrieve relevant memories
    memories = await memory.search(
        query=user_message,
        filters={"user_id": str(user.id)},
        limit=5
    )

    # 2. Format memories for prompt
    memory_context = "\n".join([
        f"- {m['memory']}" for m in memories
    ])

    # 3. Build enhanced prompt
    prompt = f"""
{SONGWRITER_SYSTEM_PROMPT}

## What I Remember About This User
{memory_context}

## Current Song
{song.to_prompt_text()}

## User Message
{user_message}
"""

    # 4. Generate response
    response = await llm.complete(prompt)

    # 5. Store new memories from this interaction
    await memory.add(
        messages=[
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": response}
        ],
        user_id=str(user.id),
        agent_id="songwriter"
    )

    return response
```

## Use Cases for Songwriter App

### 1. Learning User's Style

```python
# Automatically extracted from conversations:
memories = [
    "Prefers metaphor-heavy lyrics over literal",
    "Influenced by Taylor Swift and Phoebe Bridgers",
    "Writes primarily about relationships and self-discovery",
    "Struggles with bridge sections",
    "Likes unexpected chord changes",
    "Has been writing for 5 years",
]
```

### 2. Tracking Growth Over Time

```python
# Coach agent memories:
memories = [
    "Completed exercise on varying verse melody - showed improvement",
    "Initially struggled with iambic meter, now more consistent",
    "Feedback style preference: balanced (was encouraging, changed)",
    "Goal: Write 10 complete songs by March",
    "Finished 4 songs this month - personal best",
]
```

### 3. Cross-Session Context

```python
# User returns after a week:
User: "How's that chorus coming along?"

# Mem0 retrieves:
memories = [
    "Working on song 'Empty Chair' - stuck on chorus",
    "Tried 3 chorus variations last session",
    "Liked option B but felt it was 'too on the nose'",
]

# Agent can respond with full context:
AI: "Last time we were working on 'Empty Chair' and you liked
     the second chorus option but wanted it less literal.
     Want to try some more metaphorical approaches?"
```

### 4. Collaborative Context

```python
# For co-writing with multiple users:
memories = [
    "Sarah prefers handling melody, James handles lyrics",
    "Band decided on 'hopeful melancholy' as album theme",
    "Avoiding political topics per group decision",
]
```

## Database Schema (Self-Hosted)

```sql
-- Memories table (if using pgvector)
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    agent_id VARCHAR(50),  -- 'songwriter', 'critic', 'coach', etc.
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI embedding dimension
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for semantic search
CREATE INDEX memories_embedding_idx ON memories
USING ivfflat (embedding vector_cosine_ops);

-- Index for filtering
CREATE INDEX memories_user_agent_idx ON memories(user_id, agent_id);
```

## API Design

```python
# Memory management endpoints
@router.post("/memories")
async def add_memory(
    request: AddMemoryRequest,
    user: CurrentUser,
) -> MemoryResponse:
    """Manually add a memory (for explicit preferences)."""
    memory = await memory_service.add(
        content=request.content,
        user_id=user.id,
        agent_id=request.agent_id,
    )
    return memory


@router.get("/memories")
async def list_memories(
    user: CurrentUser,
    agent_id: str | None = None,
    limit: int = 50,
) -> list[MemoryResponse]:
    """List user's memories with optional agent filter."""
    return await memory_service.list(
        user_id=user.id,
        agent_id=agent_id,
        limit=limit,
    )


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    user: CurrentUser,
) -> None:
    """Delete a specific memory (user control over their data)."""
    await memory_service.delete(memory_id, user.id)


@router.get("/memories/search")
async def search_memories(
    query: str,
    user: CurrentUser,
    agent_id: str | None = None,
    limit: int = 5,
) -> list[MemorySearchResult]:
    """Semantic search across memories."""
    return await memory_service.search(
        query=query,
        user_id=user.id,
        agent_id=agent_id,
        limit=limit,
    )
```

## Privacy Considerations

### User Control

```python
# Users should be able to:
# 1. View all their memories
# 2. Delete specific memories
# 3. Export their memory data
# 4. Disable memory collection entirely

class PrivacySettings(BaseModel):
    memory_enabled: bool = True
    memory_retention_days: int | None = None  # None = forever
    excluded_topics: list[str] = []  # Topics to never memorize
```

### Data Handling

```python
# Filter sensitive content before storing
EXCLUDED_PATTERNS = [
    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
    r'\b\d{16}\b',  # Credit card
    r'password|secret|api.key',  # Credentials
]

async def sanitize_before_storage(content: str) -> str:
    for pattern in EXCLUDED_PATTERNS:
        content = re.sub(pattern, '[REDACTED]', content, flags=re.I)
    return content
```

## Migration Path

### Phase 1: MVP (Current)
- Database preferences only
- Explicit user settings
- No implicit memory

### Phase 2: Hybrid
- Keep explicit preferences
- Add session memory for current song context
- No cross-session memory yet

### Phase 3: Full Mem0 Integration
- Implicit memory extraction
- Cross-session continuity
- Per-agent memory
- User memory management UI

### Phase 4: Advanced Features
- Graph memory (relationships between memories)
- Memory decay (older memories fade)
- Memory consolidation (combine related memories)

## Cost Considerations

### Hosted Platform

| Plan | Price | Memories | Searches |
|------|-------|----------|----------|
| Free | $0 | 1,000 | 1,000/mo |
| Pro | $29/mo | 100,000 | Unlimited |
| Enterprise | Custom | Unlimited | Unlimited |

### Self-Hosted Costs

- LLM calls for memory extraction (~$0.001 per conversation turn)
- Embedding generation (~$0.0001 per memory)
- Vector storage (minimal, uses existing pgvector)

**Estimate:** ~$50-100/mo at 10K active users with moderate usage

## When to Adopt

### Triggers to Start Implementation

1. **MVP validated** — Users are engaged and returning
2. **Cross-session need** — Users ask "remember when we..."
3. **Agent complexity** — Multi-agent system needs shared context
4. **Personalization requests** — Users want AI to "know them better"

### Triggers to Delay

1. MVP not yet validated
2. User base too small to justify infrastructure
3. Simpler preferences system is sufficient
4. Privacy concerns in target market

## Alternatives Considered

| Alternative | Pros | Cons |
|-------------|------|------|
| **Raw conversation history** | Simple | Doesn't scale, token expensive |
| **Database preferences** | User control, simple | No implicit learning |
| **Custom embedding search** | Full control | More work to build |
| **Mem0** | Battle-tested, 59% market share | Dependency, cost |

**Decision:** Start with database preferences (MVP), migrate to Mem0 when personalization becomes a priority and user base justifies the investment.

## References

- [Mem0 Documentation](https://docs.mem0.ai)
- [Mem0 GitHub](https://github.com/mem0ai/mem0)
- [State of AI Coding 2025](https://www.greptile.com/state-of-ai-coding-2025) — 59% market share
- [LOCOMO Benchmark](https://arxiv.org/abs/2402.08716) — Memory evaluation
