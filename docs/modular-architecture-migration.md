# Greg: Modular Architecture & Migration Plan

A guide to restructuring Greg into a modular monorepo and scaling to production.

---

## Table of Contents

1. [Current vs Target Structure](#current-vs-target-structure)
2. [Migration Plan](#migration-plan)
3. [Deployment Strategies](#deployment-strategies)
4. [When to Split into Microservices](#when-to-split-into-microservices)
5. [Production Architecture](#production-architecture)

---

## Current vs Target Structure

### Current Structure (Flat)

```
greg/
├── src/
│   ├── api/routes/          # All routes mixed
│   ├── auth/                # Auth (keep)
│   ├── config/              # Config (keep)
│   ├── costs/               # Cost tracking (keep)
│   ├── database/            # Database (keep)
│   ├── jobs/                # Background jobs (keep)
│   ├── llm/                 # LLM providers (keep)
│   ├── rag/                 # RAG service (move to writer)
│   ├── ask/                 # Q&A (move to writer)
│   ├── security/            # Security (keep)
│   └── websocket/           # WebSocket (keep)
├── main.py
└── pyproject.toml
```

### Target Structure (Modular)

```
greg/
├── packages/
│   └── core/                # Shared infrastructure
│       ├── auth/
│       ├── database/
│       ├── llm/
│       ├── config/
│       ├── costs/
│       ├── jobs/
│       ├── security/
│       └── websocket/
│
├── apps/
│   ├── writer/              # Creative writing app
│   │   ├── models/
│   │   ├── services/
│   │   ├── routes/
│   │   └── frontend/
│   │
│   └── vocal/               # Vocal training app
│       ├── models/
│       ├── services/
│       ├── routes/
│       └── frontend/
│
├── main.py                  # Unified API entry point
├── pyproject.toml
└── docker-compose.yml
```

---

## Migration Plan

### Phase 1: Create Package Structure (Non-Breaking)

**Goal:** Create new folder structure without breaking existing functionality.

```bash
# Step 1: Create directories
mkdir -p packages/core
mkdir -p apps/writer/models
mkdir -p apps/writer/services
mkdir -p apps/writer/routes
mkdir -p apps/vocal/models
mkdir -p apps/vocal/services
mkdir -p apps/vocal/routes
```

**Files to create:**

```python
# packages/__init__.py
# packages/core/__init__.py
# apps/__init__.py
# apps/writer/__init__.py
# apps/vocal/__init__.py
```

### Phase 2: Move Shared Code to Core

**Move these directories to `packages/core/`:**

| From | To | Notes |
|------|-----|-------|
| `src/auth/` | `packages/core/auth/` | As-is |
| `src/database/` | `packages/core/database/` | As-is |
| `src/llm/` | `packages/core/llm/` | As-is |
| `src/config/` | `packages/core/config/` | As-is |
| `src/costs/` | `packages/core/costs/` | As-is |
| `src/jobs/` | `packages/core/jobs/` | Base job infrastructure |
| `src/security/` | `packages/core/security/` | As-is |
| `src/websocket/` | `packages/core/websocket/` | As-is |

**Update imports:**

```python
# Before
from src.auth import CurrentUser
from src.database import get_session

# After
from packages.core.auth import CurrentUser
from packages.core.database import get_session
```

**Create re-exports for backwards compatibility:**

```python
# src/auth/__init__.py (temporary, for backwards compat)
from packages.core.auth import *  # Re-export everything
```

### Phase 3: Move Writer-Specific Code

**Move RAG/writing code to writer app:**

| From | To | Notes |
|------|-----|-------|
| `src/rag/` | `apps/writer/services/rag.py` | Style-aware RAG |
| `src/ask/` | `apps/writer/services/` | Becomes completion service |
| `src/api/routes/ask.py` | `apps/writer/routes/complete.py` | Rename & refactor |
| `src/api/routes/documents.py` | `apps/writer/routes/library.py` | Rename |

**Create writer models:**

```python
# apps/writer/models/__init__.py
from .project import Project, ProjectType
from .context import Context
from .library import LibraryDocument  # Renamed from Document

# apps/writer/models/project.py
from packages.core.database import Base
# ... Project model

# apps/writer/models/context.py
from packages.core.database import Base
# ... Context model
```

**Create writer services:**

```python
# apps/writer/services/__init__.py
from .completion import CompletionService
from .style_rag import StyleRAGService
from .structure import StructureAnalyzer

# apps/writer/services/completion.py
from packages.core.llm import get_provider
from packages.core.database import get_session
from .style_rag import StyleRAGService

class CompletionService:
    """Style-aware completion using RAG."""

    async def complete(self, text: str, user_id: str) -> Completion:
        # 1. Retrieve similar content from user's library
        similar = await self.rag.retrieve(text, user_id)

        # 2. Build style-aware prompt
        prompt = self.build_prompt(text, similar)

        # 3. Generate completion
        return await self.llm.complete(prompt)
```

### Phase 4: Create Unified Main.py

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from packages.core.config import settings

# Create app
app = FastAPI(
    title="Greg",
    description="Creative tools that learn your style",
    version="2.0.0",
)

# Middleware
app.add_middleware(CORSMiddleware, ...)

# =============================================================================
# SHARED ROUTES (Core)
# =============================================================================
from packages.core.auth.routes import router as auth_router
app.include_router(auth_router, prefix="/auth", tags=["Auth"])

# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "apps": ["writer", "vocal"]}

# =============================================================================
# WRITER APP
# =============================================================================
from apps.writer.routes import projects, complete, library

app.include_router(
    projects.router,
    prefix="/writer/projects",
    tags=["Writer - Projects"]
)
app.include_router(
    complete.router,
    prefix="/writer",
    tags=["Writer - Completion"]
)
app.include_router(
    library.router,
    prefix="/writer/library",
    tags=["Writer - Library"]
)

# =============================================================================
# VOCAL APP
# =============================================================================
from apps.vocal.routes import exercises, recordings, progress

app.include_router(
    exercises.router,
    prefix="/vocal/exercises",
    tags=["Vocal - Exercises"]
)
app.include_router(
    recordings.router,
    prefix="/vocal/recordings",
    tags=["Vocal - Recordings"]
)
app.include_router(
    progress.router,
    prefix="/vocal/progress",
    tags=["Vocal - Progress"]
)
```

### Phase 5: Update Pyproject.toml

```toml
[project]
name = "greg"
version = "2.0.0"
description = "Creative tools that learn your style"

[project.scripts]
greg = "cli:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["packages*", "apps*"]
```

### Phase 6: Database Migrations

Create app-specific migrations:

```
alembic/
├── versions/
│   ├── 001_core_users.py           # Shared
│   ├── 002_core_api_keys.py        # Shared
│   ├── 003_writer_projects.py      # Writer app
│   ├── 004_writer_contexts.py      # Writer app
│   ├── 005_writer_library.py       # Writer app (documents)
│   ├── 006_vocal_exercises.py      # Vocal app
│   ├── 007_vocal_recordings.py     # Vocal app
│   └── 008_vocal_progress.py       # Vocal app
```

---

## Deployment Strategies

### Option 1: Modular Monolith (Start Here)

**Single deployable, multiple logical apps.**

```
┌─────────────────────────────────────────────────────────────────┐
│                        SINGLE CONTAINER                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      FastAPI App                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │    Auth     │  │   Writer    │  │    Vocal    │       │  │
│  │  │   /auth/*   │  │  /writer/*  │  │  /vocal/*   │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL + Redis                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Deploy:**
```yaml
# docker-compose.yml
services:
  greg:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...

  postgres:
    image: pgvector/pgvector:pg16

  redis:
    image: redis:alpine
```

**Pros:**
- Simple deployment
- Single codebase
- Shared database connections
- Easy local development

**Cons:**
- Scale everything together
- One app failure affects all

---

### Option 2: Separate Frontends, Unified Backend

**Backend stays together, frontends deploy separately.**

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTENDS                                │
│  ┌─────────────────────────┐    ┌─────────────────────────┐     │
│  │   writer.greg.app       │    │   vocal.greg.app        │     │
│  │   (Next.js on Vercel)   │    │   (Next.js on Vercel)   │     │
│  └───────────┬─────────────┘    └───────────┬─────────────┘     │
│              │                              │                    │
│              └──────────────┬───────────────┘                    │
│                             ▼                                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   api.greg.app                             │  │
│  │              (FastAPI on Railway/Fly.io)                   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Frontends scale independently (Vercel handles this)
- Backend still simple
- Different deploy cadences

**Cons:**
- CORS configuration needed
- Still single backend

---

### Option 3: App-Specific Backends (Microservices)

**Each app becomes its own service.**

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Writer    │    │    Vocal    │    │    Auth     │         │
│  │   Service   │    │   Service   │    │   Service   │         │
│  │  :8081      │    │   :8082     │    │   :8080     │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                     │
│                   ┌────────▼────────┐                           │
│                   │  API Gateway    │                           │
│                   │  (Kong/Traefik) │                           │
│                   └────────┬────────┘                           │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                 │
│         ▼                  ▼                  ▼                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Writer DB  │    │  Vocal DB   │    │   Auth DB   │         │
│  │  (Postgres) │    │  (Postgres) │    │  (Postgres) │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**When you need this:**
- Different scaling requirements (vocal needs more CPU for audio)
- Different teams working on different apps
- Isolation requirements (one app can't crash another)
- Different tech stacks per app

**Pros:**
- Scale apps independently
- Deploy apps independently
- Fault isolation

**Cons:**
- Complex infrastructure
- Service discovery needed
- Distributed transactions are hard
- Auth token validation at each service
- Overkill for solo developer

---

## When to Split into Microservices

### Stay Monolith When:

| Condition | Why |
|-----------|-----|
| Solo developer / small team | Coordination overhead not worth it |
| Apps share most data | Splitting creates sync problems |
| Similar scaling needs | No benefit to separate scaling |
| Early stage / iterating | Need to move fast |

### Consider Splitting When:

| Condition | Why Split |
|-----------|-----------|
| **Different resource needs** | Vocal needs GPU for audio, Writer doesn't |
| **Different scaling patterns** | Vocal has spiky load during practice times |
| **Team growth** | Separate teams own separate services |
| **Deployment independence** | Need to deploy Writer without touching Vocal |
| **Technology divergence** | Vocal might need Rust for audio processing |

### The Hybrid Path

**You can split incrementally:**

```
TODAY (Monolith)
────────────────
greg-api (all routes)
     │
     └── PostgreSQL


LATER (Partial Split)
─────────────────────
greg-api (/auth, /writer)
     │
     └── PostgreSQL

vocal-api (/vocal)  ← Split out when needed
     │
     └── PostgreSQL (same or separate)


EVENTUALLY (Full Split)
───────────────────────
auth-service    writer-service    vocal-service
     │               │                 │
     └───────────────┴─────────────────┘
                     │
              API Gateway
```

---

## Production Architecture

### Recommended: Start Simple, Split When Needed

**Phase 1: Deploy as Monolith**

```yaml
# Railway / Fly.io / Render
services:
  greg-api:
    image: greg:latest
    instances: 2
    health_check: /health
    env:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
```

**Phase 2: Add Worker for Background Jobs**

```yaml
services:
  greg-api:
    # ... same as above

  greg-worker:
    image: greg:latest
    command: ["python", "-m", "packages.core.jobs.worker"]
    instances: 1
```

**Phase 3: Split Frontend Deploys**

```
Vercel (Frontend)
├── writer.greg.app → apps/writer/frontend
└── vocal.greg.app  → apps/vocal/frontend

Railway (Backend)
└── api.greg.app    → Single FastAPI app
```

**Phase 4: Split Backend IF Needed**

Only if you hit scaling limits or need isolation:

```yaml
services:
  auth-service:
    routes: ["/auth/*"]

  writer-service:
    routes: ["/writer/*"]
    env:
      AUTH_SERVICE_URL: http://auth-service

  vocal-service:
    routes: ["/vocal/*"]
    env:
      AUTH_SERVICE_URL: http://auth-service
```

---

## Shared Auth in Microservices

If you do split, auth works like this:

### Option A: Auth Service + JWT Validation

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Login
       ▼
┌─────────────┐
│ Auth Service│ ──── Returns JWT
└─────────────┘
       │
       │ 2. Request with JWT
       ▼
┌─────────────┐
│Writer Service│ ──── Validates JWT locally (has public key)
└─────────────┘       No call to Auth Service needed
```

```python
# Each service validates JWT locally
from packages.core.auth.jwt import validate_token

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    token = request.headers.get("Authorization")
    if token:
        request.state.user = validate_token(token)  # Local validation
    return await call_next(request)
```

### Option B: API Gateway Handles Auth

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ API Gateway │ ──── Validates JWT, adds user to headers
└──────┬──────┘
       │ X-User-ID: 123
       ▼
┌─────────────┐
│   Services  │ ──── Trust gateway, just read header
└─────────────┘
```

---

## Summary

| Stage | Architecture | When |
|-------|--------------|------|
| **Now** | Modular Monolith | Building & iterating |
| **Users < 1000** | Monolith + Separate Frontends | Growth phase |
| **Users > 1000** | Consider splitting high-load services | Scale needs |
| **Multiple teams** | Microservices | Org growth |

**Key insight:** The modular structure you build NOW makes splitting LATER easy. You're not choosing monolith forever - you're choosing monolith first.

---

## Next Steps

1. [ ] Restructure codebase into packages/apps
2. [ ] Get Writer app working in new structure
3. [ ] Deploy monolith to Railway/Fly.io
4. [ ] Add Vocal app in same structure
5. [ ] Split only when you have a reason

---

## Commands Cheat Sheet

```bash
# Local development (monolith)
uv run greg dev

# Run just writer API locally
uv run uvicorn main:app --reload

# Run worker
uv run python -m packages.core.jobs.worker

# Deploy to Railway
railway up

# Deploy frontend to Vercel
cd apps/writer/frontend && vercel

# Run migrations
uv run alembic upgrade head
```
