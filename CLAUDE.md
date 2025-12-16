# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Greg is a modular creative writing platform with:

1. **Modular Architecture**: `packages/core/` for shared infrastructure, `apps/` for specific applications
2. **FastAPI Backend** (port 8080): Document processing, vector storage, Q&A, authentication
3. **PostgreSQL + pgvector**: User accounts, sessions, documents, vector embeddings
4. **Redis + ARQ**: Background job queue for document processing
5. **Ollama** (port 11434): Local LLM inference (Mistral, Llama, Phi, Deepseek)
6. **WebSocket**: Real-time progress updates for long-running jobs

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Start everything (Docker + migrations + API)
uv run greg dev

# Or run services individually:
uv run greg infra      # Start PostgreSQL + Redis
uv run greg migrate    # Run database migrations
uv run greg server     # Start API server
uv run greg worker     # Start background job worker
```

## CLI Commands

All commands use the `greg` CLI (via `uv run greg <command>`):

| Command | Description |
|---------|-------------|
| `dev` | Start infra, run migrations, start API server |
| `server` | Start API server only |
| `worker` | Start ARQ background worker |
| `infra` | Start PostgreSQL + Redis (docker-compose) |
| `infra-stop` | Stop infrastructure containers |
| `migrate` | Run database migrations |
| `test` | Run tests (`greg test -k "pattern"` for specific) |
| `models` | List available LLM models |
| `clean` | Clean temporary files |
| `help` | Show all commands |

## Architecture

### File Structure
```
Greg/
├── packages/
│   └── core/                    # Shared infrastructure
│       ├── admin/              # Admin services (user management, invites)
│       ├── api/                # Core API factory and routes
│       │   └── routes/         # Auth, admin, jobs, costs, models, health
│       ├── api_keys/           # API key management
│       ├── auth/               # Authentication (FastAPI-Users + extensions)
│       ├── config/             # Environment configuration
│       ├── costs/              # Cost tracking and pricing
│       ├── database/           # SQLAlchemy models and connection
│       │   └── models/         # One model per file (Rails-style)
│       ├── jobs/               # Background job infrastructure (ARQ)
│       ├── llm/                # LLM providers (Ollama, OpenAI, Anthropic, Google)
│       ├── root/               # Root endpoint schemas
│       ├── security/           # Input sanitization
│       ├── utils/              # Async I/O utilities
│       └── websocket/          # WebSocket manager and events
│
├── apps/
│   ├── writer/                  # Creative writing assistant app
│   │   ├── app.py              # App factory (extends core)
│   │   ├── jobs/               # Document processing workers
│   │   │   └── document_worker.py
│   │   ├── routes/             # Writer-specific routes
│   │   │   ├── admin/          # Document admin routes
│   │   │   ├── ask.py          # Q&A endpoint
│   │   │   ├── documents.py    # Document upload/management
│   │   │   ├── storage.py      # Storage statistics
│   │   │   └── web_search.py   # Web search
│   │   ├── services/           # Writer services
│   │   │   ├── ask/            # Q&A schemas and handlers
│   │   │   ├── documents/      # Document processing service
│   │   │   ├── rag/            # RAG query service, web search
│   │   │   ├── search/         # Web search service
│   │   │   ├── storage/        # Storage statistics service
│   │   │   ├── streaming/      # SSE streaming utilities
│   │   │   └── vectorstore/    # pgvector integration
│   │   └── models/             # Writer-specific models (if needed)
│   │
│   └── vocal/                   # Future vocal training app (placeholder)
│
├── alembic/                     # Database migrations
├── tests/                       # Test suites
├── docker-compose.yml           # PostgreSQL + Redis
├── pyproject.toml               # Dependencies and config
├── run.py                       # CLI runner
└── main.py                      # FastAPI application (runs writer app)
```

### Database Tables
```
users              # User accounts (FastAPI-Users base)
invites            # Registration invite codes
api_keys           # API key authentication
refresh_tokens     # Database-backed session management
ai_requests        # LLM request logging + cost tracking
documents          # Document metadata (S3 storage reference)
document_chunks    # Text chunks + pgvector embeddings
```

### Key Modules

**Core (packages/core/):**
- `auth/users.py` - FastAPI-Users configuration
- `auth/refresh_tokens.py` - Refresh token service
- `auth/dependencies.py` - Auth dependencies (CurrentUser, AdminUser)
- `database/models/` - One model per file (user.py, invite.py, etc.)
- `costs/tracker.py` - Cost tracking with on-the-fly aggregation
- `jobs/manager.py` - Job manager for background tasks
- `websocket/manager.py` - WebSocket connection management
- `api/app.py` - Core app factory (`create_core_app`)

**Writer App (apps/writer/):**
- `app.py` - Writer app factory (extends core)
- `services/rag/query_service.py` - RAG query execution
- `services/documents/service.py` - Document processing
- `jobs/document_worker.py` - Background document processing

### Authentication Flow
1. First user to register becomes admin automatically (no invite needed)
2. Admin creates invite codes for new users
3. Users register with invite code
4. Login returns access token (15min) + refresh token (7 days)
5. Refresh tokens rotate on each use (old token invalidated)
6. Max 10 concurrent sessions per user

### Auth Options
- **JWT**: `Authorization: Bearer <access_token>` header
- **API Key**: `X-API-Key: <key>` header (for server-to-server)

### Job Processing
Document uploads are processed asynchronously:
1. Upload returns `job_id` immediately
2. Connect to `/ws/jobs/{job_id}` for real-time progress
3. Poll `/jobs/{job_id}` for status if WebSocket unavailable

## API Endpoints

### Core Routes (packages/core)

#### Authentication
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/register` | POST | None | Register (first user = admin, others need invite) |
| `/auth/token` | POST | None | Login with JSON body, get tokens |
| `/auth/refresh` | POST | None | Exchange refresh token for new tokens |
| `/auth/logout` | POST | None | Revoke refresh token |
| `/auth/logout-all` | POST | JWT | Revoke all sessions |
| `/auth/me` | GET | JWT | Get current user profile |
| `/auth/sessions` | GET | JWT | List active sessions |
| `/auth/sessions/{id}` | DELETE | JWT | Revoke specific session |

#### Jobs (Background Tasks)
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/jobs/{id}` | GET | JWT | Get job status |
| `/jobs/{id}/cancel` | POST | JWT | Cancel a job |
| `/jobs` | GET | Admin | List all jobs |

#### Costs
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/costs` | GET | JWT | Daily cost summary |
| `/costs/requests` | GET | JWT | Recent AI requests |
| `/costs/total` | GET | JWT | Total cost for period |

#### API Keys
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api-keys/` | POST | JWT | Create API key |
| `/api-keys/` | GET | JWT | List your API keys |
| `/api-keys/{id}` | DELETE | JWT | Revoke API key |

#### Admin
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/admin/users` | GET | Admin | List all users |
| `/admin/users/{id}` | GET | Admin | Get user details |
| `/admin/users/{id}` | PATCH | Admin | Update user role |
| `/admin/users/{id}` | DELETE | Admin | Delete user |
| `/admin/invites` | POST | Admin | Create invite code |
| `/admin/invites` | GET | Admin | List invites |
| `/admin/invites/{code}` | DELETE | Admin | Revoke invite |

#### System
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/` | GET | None | API info |
| `/health` | GET | None | System health check |
| `/models` | GET | None | List available LLM models |
| `/docs` | GET | None | OpenAPI documentation |

#### WebSocket
| Endpoint | Description |
|----------|-------------|
| `/ws/jobs/{job_id}` | Subscribe to specific job progress |
| `/ws` | General WebSocket (subscribe to multiple jobs) |

### Writer App Routes (apps/writer)

#### Documents
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/documents` | GET | JWT | List processed documents |
| `/documents` | POST | JWT | Upload document (returns job_id) |
| `/documents/{id}` | DELETE | JWT | Delete a document |
| `/documents/url` | POST | JWT | Process URL as document |
| `/admin/documents` | DELETE | Admin | Clear all documents |

#### Q&A
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/ask` | POST | JWT | Ask a question (streaming SSE or JSON) |
| `/web-search` | POST | JWT | Web search query (streaming SSE) |

#### Storage
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/storage` | GET | JWT | Vector store statistics |

## Testing

```bash
# Run all tests
uv run greg test

# Run specific tests
uv run greg test -k "test_auth"
uv run greg test -k "test_documents"
uv run greg test tests/api/

# Run with verbose output
uv run greg test -v
```

### Test Structure
- `tests/unit/` - Fast unit tests
- `tests/api/` - API endpoint tests
- `tests/integration/` - Service integration tests

## Environment Variables

Key variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://greg:greg@localhost:5432/greg

# Redis
REDIS_URL=redis://localhost:6379

# JWT
JWT_SECRET_KEY=your-secret-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=15

# Refresh Tokens
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_SESSIONS_PER_USER=10

# LLM Provider
LLM_PROVIDER=ollama
LLM_MODEL=mistral

# Paid API Keys (optional)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
```

See `.env.example` for full list.

## Database Migrations

```bash
# Run pending migrations
uv run greg migrate

# Create new migration
uv run alembic revision --autogenerate -m "description"

# Rollback one migration
uv run alembic downgrade -1
```

### Current Migrations
1. `001_create_users_table` - Users with FastAPI-Users fields
2. `002_create_invites_table` - Invite codes
3. `003_create_api_keys_table` - API key authentication
4. `004_create_ai_requests_table` - LLM request logging
5. `005_create_documents_table` - Document metadata
6. `006_create_document_chunks_table` - Chunks with pgvector
7. `007_create_refresh_tokens_table` - Session management

## Common Tasks

### Add a Core Route (shared across apps)
1. Create route file in `packages/core/api/routes/`
2. Add router to `packages/core/api/routes/__init__.py`
3. Add router to `packages/core/api/app.py` in `_register_core_routes()`
4. Add auth dependencies as needed (`CurrentUser`, `AdminUser`)

### Add a Writer App Route
1. Create route file in `apps/writer/routes/`
2. Import and register in `apps/writer/app.py` `register_writer_routes()`
3. Add exception handlers if needed

### Add a Background Job (Writer)
1. Create job function in `apps/writer/jobs/document_worker.py`
2. Add to `WorkerSettings.functions` in `packages/core/jobs/worker.py`
3. Enqueue with `job_manager.create_job()`

### Add a Core Model (shared)
1. Create model file in `packages/core/database/models/`
2. Export from `packages/core/database/models/__init__.py`
3. Export from `packages/core/database/__init__.py`
4. Create migration with `uv run alembic revision --autogenerate -m "add X table"`

### Create a New App
1. Create `apps/newapp/` directory
2. Create `apps/newapp/app.py`:
```python
from packages.core.api.app import create_core_app
from apps.newapp.routes import feature1, feature2

def register_routes(app):
    app.include_router(feature1.router)
    app.include_router(feature2.router)

def create_app():
    return create_core_app(
        title="New App",
        extra_routes_registrar=register_routes,
    )
```
3. Create a new `main_newapp.py` or update `main.py` to run the new app

## Best Practices

1. **Authentication**: All new routes should require auth unless public
2. **Imports**: Use `from packages.core.module` or `from apps.writer.module` format
3. **Async**: All database and I/O operations should be async
4. **Validation**: Use Pydantic models for request/response schemas
5. **Errors**: Return proper HTTP status codes with detail messages
6. **Models**: One model per file in `packages/core/database/models/`
7. **Core vs App**: Put shared functionality in `packages/core/`, app-specific in `apps/<app>/`

## Code Conventions

### Route File Structure

```python
"""
Module description.

Brief explanation of what this module provides.

Endpoints:
    POST   /resource/          - Create resource
    GET    /resource/          - List resources
    DELETE /resource/{id}      - Delete resource
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.auth import CurrentUser
from packages.core.database import Model, get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resource", tags=["Resource"])


# Public functions

@router.post("/", response_model=CreateResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    request: CreateRequest,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """Create a new resource."""
    # Implementation
    logger.info(f"User {user.email} created resource")
    return response


# Private functions

def _helper_function(arg: Type) -> ReturnType:
    """Helper function description."""
    return result
```

### Section Comments

Use single blank line after section comments:

```python
# Public functions

@router.get("/")
async def list_items():
    ...


# Private functions

def _helper():
    ...
```

### Dependency Injection

Use type aliases and `Annotated` for clean signatures:

```python
# Good - type alias for common dependencies
async def get_item(user: CurrentUser):
    ...

# Good - Annotated for session
async def list_items(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    ...

# Avoid - verbose inline Depends
async def get_item(user: Annotated[User, Depends(current_active_user)]):
    ...
```

### Logging

- Log security/audit events (login, logout, key creation/revocation)
- Don't log routine read operations (Uvicorn handles access logs)
- Use f-strings with user context: `logger.info(f"User {user.email} did action")`

### Imports

Organize in groups, alphabetized within each:

1. Standard library (`import logging`, `from typing import ...`)
2. Third-party (`from fastapi import ...`, `from sqlalchemy import ...`)
3. Core packages (`from packages.core.auth import ...`, `from packages.core.database import ...`)
4. App-specific (`from apps.writer.services import ...`)
