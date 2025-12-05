# Greg

A production-ready RAG (Retrieval-Augmented Generation) API for document Q&A with multi-provider LLM support.

## Features

- **Document Processing** - Upload PDFs, TXT, CSV, Markdown, Word, Excel, and images
- **Vector Search** - PostgreSQL + pgvector for semantic similarity search
- **Multi-Provider LLMs** - Ollama (local/free), OpenAI, Anthropic, Google
- **Real-time Progress** - WebSocket updates for document processing
- **Authentication** - JWT access tokens + refresh tokens + API keys
- **Cost Tracking** - Per-request logging with daily/monthly aggregation
- **Background Jobs** - Async document processing with Redis + ARQ

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (for PostgreSQL + Redis)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [Ollama](https://ollama.ai/) (optional, for local LLMs)

### 1. Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd greg

# Copy environment file
cp .env.example .env
```

### 2. Start Everything

```bash
uv run greg dev
```

This single command:
1. Starts PostgreSQL + Redis (Docker)
2. Waits for services to be ready
3. Runs database migrations
4. Starts Ollama (if installed)
5. Starts the API server

**API available at:** http://localhost:8080
**API docs at:** http://localhost:8080/docs

### 3. Register Admin Account

The **first user to register becomes admin** automatically (no invite code needed):

```bash
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "your-secure-password"}'
```

### 4. Login

```bash
curl -X POST http://localhost:8080/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=your-secure-password"
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "abc123...",
  "token_type": "bearer"
}
```

### 5. Use the API

```bash
# Upload a document
curl -X POST http://localhost:8080/documents \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@document.pdf"

# Ask a question (streaming response)
curl -X POST http://localhost:8080/ask \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

## CLI Commands

All commands use `uv run greg <command>`:

| Command | Description |
|---------|-------------|
| `dev` | **Start everything** - Docker, migrations, API server |
| `server` | Start API server only |
| `worker` | Start background job worker |
| `infra` | Start PostgreSQL + Redis (Docker) |
| `infra-stop` | Stop PostgreSQL + Redis |
| `migrate` | Run database migrations |
| `test` | Run test suite |
| `models` | List available LLM models |
| `clean` | Clean temporary files |
| `help` | Show all commands |

### Aliases

| Alias | Same as |
|-------|---------|
| `start` | `dev` |
| `api` | `server` |
| `up` | `infra` |
| `down` | `infra-stop` |
| `db` | `migrate` |

### Examples

```bash
# Start full dev environment
uv run greg dev

# Or start services separately
uv run greg infra          # Start Docker containers
uv run greg migrate        # Run migrations
uv run greg server         # Start API

# Run tests
uv run greg test
uv run greg test -k "test_auth"    # Run specific tests

# Check available models
uv run greg models
```

## API Endpoints

### Public (No Auth Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/models` | List LLM models |
| GET | `/docs` | OpenAPI documentation |

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register (first user = admin) |
| POST | `/auth/login` | Login → access + refresh tokens |
| POST | `/auth/refresh` | Exchange refresh token for new tokens |
| POST | `/auth/logout` | Revoke refresh token |
| POST | `/auth/logout-all` | Revoke all sessions |
| GET | `/auth/me` | Get current user |
| GET | `/auth/sessions` | List active sessions |
| DELETE | `/auth/sessions/{id}` | Revoke specific session |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents` | Upload document (returns job_id) |
| POST | `/documents/url` | Process URL as document |
| GET | `/documents` | List all documents |
| DELETE | `/documents/{id}` | Delete document |
| DELETE | `/documents` | Clear all (admin only) |

### Q&A

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ask` | Ask question (streaming SSE) |
| POST | `/web-search` | Web search (streaming SSE) |

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/jobs/{id}` | Get job status |
| POST | `/jobs/{id}/cancel` | Cancel job |
| GET | `/jobs` | List all jobs (admin only) |

### Costs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/costs` | Daily cost summary |
| GET | `/costs/requests` | Recent AI requests |
| GET | `/costs/total` | Total cost for period |

### API Keys

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api-keys/` | Create API key |
| GET | `/api-keys/` | List your API keys |
| DELETE | `/api-keys/{id}` | Revoke API key |

### Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/users` | List all users |
| PATCH | `/admin/users/{id}` | Update user role |
| DELETE | `/admin/users/{id}` | Delete user |
| POST | `/admin/invites` | Create invite code |
| GET | `/admin/invites` | List invites |
| DELETE | `/admin/invites/{code}` | Revoke invite |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/jobs/{job_id}` | Subscribe to job progress |
| `/ws` | General WebSocket connection |

## Authentication

### Three Auth Methods

1. **JWT Access Token** (browser/app sessions)
   ```
   Authorization: Bearer <access_token>
   ```
   - Short-lived (15 minutes default)
   - Use refresh token to get new ones

2. **Refresh Token** (session management)
   - Long-lived (7 days default)
   - Rotates on each use (old token invalidated)
   - Database-backed (can be revoked)

3. **API Key** (server-to-server)
   ```
   X-API-Key: greg_abc123...
   ```
   - No expiry (manually revocable)
   - Good for scripts, CI/CD, integrations

### First User = Admin

The first user to register automatically becomes admin. No invite code needed.

Subsequent users need an invite code:

```bash
# Admin creates invite
curl -X POST http://localhost:8080/admin/invites \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{"expires_in_days": 7}'

# Response: {"code": "ABC123", ...}

# New user registers with invite
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "pass", "invite_code": "ABC123"}'
```

## Configuration

### Environment Variables

Key variables in `.env`:

```bash
# Database
DATABASE_URL=postgresql://greg:greg@localhost:5432/greg

# Redis (for background jobs)
REDIS_URL=redis://localhost:6379

# JWT Security (CHANGE IN PRODUCTION!)
JWT_SECRET_KEY=change-this-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_SESSIONS_PER_USER=10

# Default LLM (local Ollama)
LLM_PROVIDER=ollama
LLM_MODEL=mistral

# Optional: Paid LLM Providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

### LLM Providers

**Local (Ollama)** - Free, private, runs on your machine:
```bash
# Install Ollama from https://ollama.ai
ollama pull mistral    # Recommended: good balance
ollama pull phi        # Faster, smaller
ollama pull llama2     # Alternative
```

**Cloud Providers** - Set API keys in `.env`:
- **OpenAI**: `OPENAI_API_KEY=sk-...`
- **Anthropic**: `ANTHROPIC_API_KEY=sk-ant-...`
- **Google**: `GOOGLE_API_KEY=...`

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│  Client / App   │────▶│  FastAPI (8080)  │
└─────────────────┘     └────────┬─────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐    ┌───────────────────┐    ┌──────────────────┐
│  PostgreSQL   │    │   Redis + ARQ     │    │     Ollama       │
│  + pgvector   │    │  (Background Jobs)│    │  (Local LLMs)    │
└───────────────┘    └───────────────────┘    └──────────────────┘
```

### Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts |
| `invites` | Registration invite codes |
| `api_keys` | API key authentication |
| `refresh_tokens` | Session management |
| `ai_requests` | LLM request logging + costs |
| `documents` | Document metadata |
| `document_chunks` | Text chunks + vector embeddings |

### Project Structure

```
├── src/
│   ├── api/            # FastAPI routes
│   │   └── routes/     # Endpoint modules
│   ├── auth/           # Authentication (JWT, refresh tokens, API keys)
│   ├── costs/          # Cost tracking
│   ├── database/       # SQLAlchemy models
│   │   └── models/     # One model per file
│   ├── jobs/           # Background workers (ARQ)
│   └── websocket/      # WebSocket handlers
├── alembic/            # Database migrations
├── tests/              # Test suites
├── docker-compose.yml  # PostgreSQL + Redis
├── pyproject.toml      # Dependencies
├── run.py              # CLI entry point
└── main.py             # FastAPI application
```

## Development

### Running Tests

```bash
# All tests
uv run greg test

# Specific tests
uv run greg test -k "test_auth"
uv run greg test -k "test_documents"

# Verbose output
uv run greg test -v
```

### Database Migrations

```bash
# Run pending migrations
uv run greg migrate

# Create new migration
uv run alembic revision --autogenerate -m "add new table"

# Rollback
uv run alembic downgrade -1
```

### Adding a New Endpoint

1. Create route file in `src/api/routes/`
2. Add router to `src/api/app.py`
3. Add auth as needed (`CurrentUser`, `AdminUser`)

### Adding a Database Model

1. Create model in `src/database/models/`
2. Export from `src/database/models/__init__.py`
3. Export from `src/database/__init__.py`
4. Create migration: `uv run alembic revision --autogenerate -m "description"`

## WebSocket Usage

### Job Progress Updates

```javascript
// Connect to job progress
const ws = new WebSocket('ws://localhost:8080/ws/jobs/{job_id}');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'job.progress':
      console.log(`Progress: ${data.data.percent}%`);
      break;
    case 'job.completed':
      console.log('Done!', data.data.result);
      break;
    case 'job.failed':
      console.error('Failed:', data.data.error);
      break;
  }
};
```

## Troubleshooting

### Docker not running
```bash
# Start Docker Desktop, then:
uv run greg infra
```

### Port already in use
```bash
# Check what's using port 8080
lsof -i :8080

# Kill it or use different port
PORT=8081 uv run greg server
```

### Database connection failed
```bash
# Make sure PostgreSQL is running
docker compose ps

# Check logs
docker compose logs postgres
```

### Ollama not responding
```bash
# Check if Ollama is running
ollama list

# Start it
ollama serve
```

## License

MIT
