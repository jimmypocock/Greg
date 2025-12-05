# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Greg is a production-ready RAG (Retrieval-Augmented Generation) system with:

1. **FastAPI Backend** (port 8080): Document processing, vector storage, Q&A, authentication
2. **PostgreSQL**: User accounts, invites, API keys, sessions
3. **Redis + ARQ**: Background job queue for document processing
4. **Ollama** (port 11434): Local LLM inference (Mistral, Llama, Phi, Deepseek)
5. **WebSocket**: Real-time progress updates for long-running jobs

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

## API Endpoints

### Authentication
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/auth/signup` | POST | None | Register (invite code required) |
| `/auth/login` | POST | None | Login, get JWT tokens |
| `/auth/refresh` | POST | Refresh Token | Refresh access token |
| `/auth/logout` | POST | JWT | Logout, revoke tokens |
| `/auth/me` | GET | JWT | Get current user profile |

### Documents
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/documents` | GET | JWT | List processed documents |
| `/documents` | POST | JWT | Upload document (returns job_id) |
| `/documents/{id}` | DELETE | JWT | Delete a document |
| `/documents/clear` | POST | Admin | Clear all documents |
| `/documents/url` | POST | JWT | Process URL as document |

### Q&A
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/ask` | POST | JWT | Ask a question (streaming) |
| `/search` | POST | JWT | Web search query |

### Jobs (Background Tasks)
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/jobs/{id}` | GET | JWT | Get job status |
| `/jobs/{id}` | DELETE | JWT | Cancel a job |
| `/jobs` | GET | Admin | List all jobs |
| `/ws/jobs/{id}` | WS | None | Real-time job progress |

### Admin
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/admin/users` | GET | Admin | List all users |
| `/admin/users/{id}` | PATCH | Admin | Update user role/tier |
| `/admin/invites` | GET/POST | Admin | Manage invite codes |
| `/api-keys` | GET/POST/DELETE | JWT | Manage API keys |

### System
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | None | System health check |
| `/models` | GET | JWT | List available LLM models |
| `/storage` | GET | JWT | Vector store statistics |
| `/docs` | GET | None | OpenAPI documentation |

## Architecture

### File Structure
```
/
├── documents/           # User documents (gitignored)
├── src/
│   ├── api/            # FastAPI routes and dependencies
│   │   └── routes/     # Route modules (ask, auth, documents, etc.)
│   ├── auth/           # Authentication (JWT, passwords, API keys)
│   ├── database/       # SQLAlchemy models and connection
│   ├── jobs/           # Background job processing (ARQ)
│   ├── llm/            # LLM provider integrations
│   ├── websocket/      # WebSocket manager and events
│   ├── config.py       # Environment configuration
│   ├── security.py     # Input sanitization
│   └── *.py            # Core modules
├── alembic/            # Database migrations
├── tests/              # Test suites
├── docker-compose.yml  # PostgreSQL + Redis
├── pyproject.toml      # Dependencies and config
├── run.py              # CLI runner
└── main.py             # FastAPI application
```

### Key Modules
- `src/config.py`: Environment configuration
- `src/database/models.py`: User, Invite, APIKey, RefreshToken models
- `src/auth/`: JWT tokens, password hashing, dependencies
- `src/jobs/`: ARQ worker, job manager, document processing
- `src/websocket/manager.py`: WebSocket connection management
- `src/unified_document_processor.py`: Document chunking and indexing
- `src/qa_chain_unified.py`: RAG query processing with streaming

### Authentication Flow
1. First user to register becomes admin automatically
2. Admin creates invite codes for new users
3. Users register with invite code
4. Login returns access token (15min) + refresh token (7 days)
5. Access token in `Authorization: Bearer <token>` header
6. Or use API key in `X-API-Key` header

### User Tiers
- **Free**: Local models only (Ollama)
- **Pro**: Access to paid APIs (OpenAI, Anthropic, Google)

Admin can upgrade users via `/admin/users/{id}` endpoint.

### Job Processing
Document uploads are processed asynchronously:
1. Upload returns `job_id` immediately
2. Connect to `/ws/jobs/{job_id}` for real-time progress
3. Poll `/jobs/{job_id}` for status if WebSocket unavailable

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

# JWT (CHANGE IN PRODUCTION!)
JWT_SECRET_KEY=your-secret-key

# LLM Provider
LLM_PROVIDER=ollama
LLM_MODEL=mistral

# Paid API Keys (Pro tier only)
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

## Common Tasks

### Add a New Route
1. Create route file in `src/api/routes/`
2. Add router to `src/api/__init__.py`
3. Add auth dependencies as needed (`CurrentUser`, `AdminUser`, `ProUser`)

### Add a Background Job
1. Create job function in `src/jobs/document_worker.py`
2. Add to `WorkerSettings.functions` in `src/jobs/worker.py`
3. Enqueue with `enqueue_job("function_name", *args, **kwargs)`

### Test Paid Models
Requires Pro tier. Set API keys in `.env`, then:
```json
POST /ask
{
  "question": "Hello",
  "model_name": "gpt-4o-mini"
}
```

## Best Practices

1. **Authentication**: All new routes should require auth unless public
2. **Imports**: Use `from src.module` format, never relative imports
3. **Async**: All database and I/O operations should be async
4. **Validation**: Use Pydantic models for request/response schemas
5. **Errors**: Return proper HTTP status codes with detail messages
