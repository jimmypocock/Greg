# GraphRAG Implementation Plan

> **Status:** Future enhancement - document existing features first

## Overview

Enhance Greg's RAG system with a knowledge graph to enable:
- Multi-document relationship understanding
- Multi-hop reasoning
- Claude Projects-like experience
- Persistent knowledge from web searches

## Current State (Vector RAG)

```
Document → Chunks → Embeddings → pgvector

Query → Embed → Find similar vectors → Return chunks → LLM answers
```

**Limitation:** Chunks have no relationship to each other beyond vector similarity. Can't answer questions requiring reasoning across documents.

## Proposed State (GraphRAG)

```
                    ┌─────────────────┐
                    │   Your Query    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                              ▼
    ┌─────────────────┐            ┌─────────────────┐
    │  Vector Search  │            │  Graph Traverse │
    └────────┬────────┘            └────────┬────────┘
             │                              │
             └──────────────┬───────────────┘
                            ▼
                   ┌─────────────────┐
                   │  Combined Context│
                   │  + Relationships │
                   └────────┬────────┘
                            ▼
                   ┌─────────────────┐
                   │      LLM        │
                   └─────────────────┘
```

## Use Cases

### 1. Claude Projects-like Experience

Group related documents into projects. Knowledge graph connects entities across all docs in a project.

```
Project: "Q4 Planning"
├── budget.xlsx → entities: [Q4 Budget, Marketing: $50k, Engineering: $100k]
├── roadmap.md → entities: [Feature X, Feature Y, Launch: March]
├── team.pdf → entities: [Alice: PM, Bob: Eng Lead]
└── Knowledge Graph connects them all

Query: "Can we afford Feature X with current budget?"
→ Graph traverses: Feature X → Engineering → costs → budget
→ Retrieves relevant chunks from multiple docs
```

### 2. Books / Large Documents

Preserve structure that chunking destroys:

```
[Character: John] --appears_in--> [Chapter 1, 3, 5]
[Character: John] --related_to--> [Character: Mary]
[Concept: The War] --mentioned_in--> [Chapter 2, 5, 7]
[Chapter 5] --references--> [Chapter 1 events]

Query: "How does John's relationship with Mary evolve?"
→ Traverses John → Mary → all chapters mentioning both → chronological context
```

### 3. Enterprise Document Processing

Companies have interconnected documents:

```
[Policy: PTO-001] --supersedes--> [Policy: PTO-2019]
[Policy: PTO-001] --applies_to--> [Department: Engineering]
[Employee: Alice] --member_of--> [Department: Engineering]

Query: "What PTO policy applies to engineering managers?"
→ Traverse: Manager role → Engineering dept → PTO-001
```

### 4. Multi-hop Web Search (Agentic RAG)

Chain searches together, building persistent knowledge:

```
Query: "What's the market cap of the company that acquired the creator of ChatGPT?"

Step 1: Check graph - do we know this?
Step 2: Search: "Who created ChatGPT" → OpenAI
Step 3: Search: "Who acquired OpenAI" → Microsoft (investment)
Step 4: Search: "Microsoft market cap" → Answer
Step 5: Store all entities in graph for future queries
```

## Database Schema

### New Tables

```sql
-- Entities extracted from docs/searches
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    entity_type TEXT,           -- person, company, concept, date, location, etc.
    normalized_name TEXT,       -- lowercase, trimmed for matching
    source_type TEXT,           -- document, web_search, user_input
    source_id UUID,             -- document_id or search_id
    chunk_id UUID REFERENCES document_chunks(id),
    user_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    CONSTRAINT unique_entity_per_user UNIQUE (normalized_name, entity_type, user_id)
);

CREATE INDEX idx_entities_user ON entities(user_id);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_name ON entities(normalized_name);

-- Relationships between entities
CREATE TABLE entity_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    to_entity_id UUID REFERENCES entities(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,  -- works_at, created, mentions, parent_of, etc.
    confidence FLOAT DEFAULT 1.0,     -- LLM confidence in extraction
    source_chunk_id UUID REFERENCES document_chunks(id),
    user_id UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    CONSTRAINT unique_relationship UNIQUE (from_entity_id, to_entity_id, relationship_type)
);

CREATE INDEX idx_relationships_from ON entity_relationships(from_entity_id);
CREATE INDEX idx_relationships_to ON entity_relationships(to_entity_id);
CREATE INDEX idx_relationships_type ON entity_relationships(relationship_type);

-- Projects (like Claude Desktop)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_projects_user ON projects(user_id);

-- Link documents to projects (many-to-many)
CREATE TABLE project_documents (
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    PRIMARY KEY (project_id, document_id)
);
```

## API Endpoints

### Projects

```
POST   /projects                      - Create project
GET    /projects                      - List user's projects
GET    /projects/{id}                 - Get project details
PATCH  /projects/{id}                 - Update project
DELETE /projects/{id}                 - Delete project

POST   /projects/{id}/documents       - Add document to project
DELETE /projects/{id}/documents/{doc} - Remove document from project
GET    /projects/{id}/documents       - List project documents

GET    /projects/{id}/graph           - Get knowledge graph for project
POST   /projects/{id}/ask             - Ask question with project context
```

### Entities (Admin/Debug)

```
GET    /entities                      - List entities (filterable)
GET    /entities/{id}                 - Get entity details
GET    /entities/{id}/connections     - Get entity relationships
DELETE /entities/{id}                 - Delete entity
```

## Implementation Phases

### Phase 1: Projects

**Goal:** Group documents into projects for scoped queries.

1. Add `projects` and `project_documents` tables
2. Create project CRUD endpoints
3. Modify `/ask` to accept optional `project_id`
4. Filter document retrieval by project

**No entity extraction yet** - just document grouping.

### Phase 2: Entity Extraction

**Goal:** Extract and store entities during document processing.

1. Add `entities` and `entity_relationships` tables
2. Create entity extraction prompt for LLM
3. Integrate extraction into document processing job
4. Add entity listing endpoints

**Extraction prompt example:**
```
Extract all named entities and their relationships from this text.

Return JSON:
{
  "entities": [
    {"name": "John Smith", "type": "person"},
    {"name": "Acme Corp", "type": "company"}
  ],
  "relationships": [
    {"from": "John Smith", "to": "Acme Corp", "type": "works_at"}
  ]
}

Text:
{chunk_text}
```

### Phase 3: Graph-Enhanced Retrieval

**Goal:** Use graph traversal alongside vector search.

1. Implement graph traversal queries (N-hop neighbors)
2. Create hybrid retrieval function
3. Rank results by combined vector + graph score
4. Include relationship paths in context

**Hybrid retrieval:**
```python
async def hybrid_retrieve(
    question: str,
    project_id: UUID | None,
    vector_weight: float = 0.6,
    graph_weight: float = 0.4,
    max_hops: int = 2,
) -> list[RetrievedChunk]:
    # 1. Vector search
    vector_results = await vector_search(question, project_id)

    # 2. Extract entities from question
    query_entities = await extract_entities(question)

    # 3. Graph traversal from query entities
    graph_results = await graph_traverse(query_entities, max_hops)

    # 4. Score and merge
    return merge_and_rank(vector_results, graph_results, vector_weight, graph_weight)
```

### Phase 4: Multi-hop Web Search

**Goal:** Chain web searches with graph-based reasoning.

1. Add query decomposition (break complex queries into steps)
2. Implement search loop with graph updates
3. Store web search entities in graph
4. Add stopping condition (answer found or max hops)

**Agentic loop:**
```python
async def multi_hop_search(question: str, max_hops: int = 3):
    for hop in range(max_hops):
        # 1. What do we need to know?
        needed = await identify_missing_info(question, graph)

        if not needed:
            break  # We can answer

        # 2. Search for missing info
        search_query = await generate_search_query(needed[0])
        results = await web_search(search_query)

        # 3. Extract and store entities
        entities = await extract_entities(results)
        await store_in_graph(entities)

    # 4. Answer with full context
    return await generate_answer(question, graph)
```

## Graph Visualization

Consider adding a visualization endpoint that returns graph data in a format suitable for D3.js or similar:

```json
{
  "nodes": [
    {"id": "uuid1", "name": "John Smith", "type": "person"},
    {"id": "uuid2", "name": "Acme Corp", "type": "company"}
  ],
  "edges": [
    {"source": "uuid1", "target": "uuid2", "type": "works_at"}
  ]
}
```

## Performance Considerations

- **Entity extraction adds latency** to document processing (LLM call per chunk)
- **Graph queries** can be expensive for large graphs (limit hops, use indexes)
- **Consider caching** frequently traversed paths
- **Batch entity extraction** where possible
- **Use background jobs** for graph building (don't block uploads)

## Alternative: Graph Database

If graph queries become complex, consider Neo4j or similar:

**Pros:**
- Native graph traversal (Cypher queries)
- Optimized for relationship queries
- Built-in visualization tools

**Cons:**
- Another database to manage
- Data sync between PostgreSQL and Neo4j
- Additional infrastructure cost

**Recommendation:** Start with PostgreSQL tables. Migrate to Neo4j only if query complexity demands it.

## References

- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [LlamaIndex Knowledge Graphs](https://docs.llamaindex.ai/en/stable/examples/index_structs/knowledge_graph/)
- [Neo4j + LangChain](https://python.langchain.com/docs/integrations/graphs/neo4j_cypher)
