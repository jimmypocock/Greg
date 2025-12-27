# Architecture Patterns & Scaling Guidelines

> **Purpose:** Ensure consistent, scalable patterns as the codebase grows.

## Current Structure

```
Greg/
├── api/                    # Main API application
│   ├── auth/              # Authentication
│   ├── billing/           # Stripe integration
│   ├── routes/            # HTTP endpoints
│   ├── services/          # Business logic
│   └── models/            # SQLAlchemy models
├── web/                    # Next.js frontend
├── alembic/               # Database migrations
├── packages/
│   └── cli/               # CLI tools
└── docs/                  # Documentation
```

---

## 1. Service Layer Pattern

**Principle:** Routes handle HTTP concerns only. Business logic lives in services.

### Current (Mixed)
```python
# Routes contain business logic - avoid this
@router.post("/songs")
async def create_song(request: CreateSongRequest, session: AsyncSession):
    song = Song(title=request.title, user_id=user.id)
    session.add(song)
    await session.commit()
    # 50 more lines of business logic...
    return song
```

### Target (Separated)
```python
# api/routes/songs.py - HTTP concerns only
@router.post("/songs")
async def create_song(
    request: CreateSongRequest,
    user: CurrentUser,
    song_service: Annotated[SongService, Depends(get_song_service)],
) -> SongResponse:
    song = await song_service.create(request, user)
    return SongResponse.from_orm(song)


# api/services/song_service.py - Business logic
class SongService:
    def __init__(self, session: AsyncSession, style_library: StyleLibrary):
        self.session = session
        self.style_library = style_library

    async def create(self, request: CreateSongRequest, user: User) -> Song:
        song = Song(title=request.title, user_id=user.id)
        self.session.add(song)
        await self.session.commit()

        # Index in style library
        await self.style_library.index_song(song)

        return song
```

### Benefits
- Testable: Mock services, not HTTP
- Reusable: Services callable from jobs, CLI, etc.
- Clear: Routes are thin, services are focused

---

## 2. Dependency Injection

**Principle:** Use FastAPI's `Depends()` for all dependencies.

### Service Dependencies
```python
# api/dependencies.py

async def get_song_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    style_library: Annotated[StyleLibrary, Depends(get_style_library)],
) -> SongService:
    return SongService(session, style_library)


async def get_style_library(
    session: Annotated[AsyncSession, Depends(get_session)],
    embeddings: Annotated[EmbeddingService, Depends(get_embeddings)],
) -> StyleLibrary:
    return StyleLibrary(session, embeddings)
```

### Type Aliases for Clean Signatures
```python
# api/auth/dependencies.py

# Instead of verbose inline Depends
async def endpoint(user: Annotated[User, Depends(current_active_user)]):
    ...

# Use type alias
CurrentUser = Annotated[User, Depends(current_active_user)]
AdminUser = Annotated[User, Depends(require_admin)]

async def endpoint(user: CurrentUser):
    ...
```

---

## 3. Domain Exceptions

**Principle:** Raise domain exceptions, convert to HTTP in routes.

### Define Domain Exceptions
```python
# api/exceptions.py

class DomainError(Exception):
    """Base for all domain errors."""
    pass


class NotFoundError(DomainError):
    """Resource not found."""
    def __init__(self, resource: str, id: str):
        self.resource = resource
        self.id = id
        super().__init__(f"{resource} not found: {id}")


class ValidationError(DomainError):
    """Invalid input."""
    pass


class InsufficientCreditsError(DomainError):
    """User doesn't have enough credits."""
    pass


class StyleLibraryError(DomainError):
    """Style library operation failed."""
    pass
```

### Exception Handlers
```python
# api/app.py

@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )


@app.exception_handler(InsufficientCreditsError)
async def credits_handler(request: Request, exc: InsufficientCreditsError):
    return JSONResponse(
        status_code=402,
        content={"detail": "Insufficient credits"},
    )
```

### Usage in Services
```python
# Services raise domain exceptions
class SongService:
    async def get(self, song_id: UUID, user_id: UUID) -> Song:
        song = await self.session.get(Song, song_id)
        if not song or song.user_id != user_id:
            raise NotFoundError("Song", str(song_id))
        return song
```

---

## 4. Background Jobs for AI

**Principle:** AI operations should be async jobs, not blocking requests.

### Why?
- LLM calls can take 5-30+ seconds
- User sees immediate feedback
- Can retry failed jobs
- Better resource management

### Pattern
```python
# api/routes/songs.py

@router.post("/{song_id}/suggest-structure")
async def suggest_structure(
    song_id: UUID,
    user: CurrentUser,
    job_manager: Annotated[JobManager, Depends(get_job_manager)],
) -> JobResponse:
    """Queue AI structure suggestion (returns immediately)."""
    job = await job_manager.create_job(
        "suggest_song_structure",
        user_id=user.id,
        song_id=str(song_id),
    )
    return JobResponse(job_id=job.id, status="queued")


# api/jobs/song_jobs.py

async def suggest_song_structure_job(ctx: dict, song_id: str) -> dict:
    """Background job for AI suggestion."""
    song = await get_song(UUID(song_id))
    suggestion = await ai_service.analyze_structure(song)
    return {"suggestion": suggestion.dict()}
```

### Client Polling
```typescript
// Frontend polls for job completion
const { data: job } = useQuery({
  queryKey: ['job', jobId],
  queryFn: () => api.get(`/jobs/${jobId}`),
  refetchInterval: (data) => data?.status === 'completed' ? false : 1000,
});
```

---

## 5. Caching Strategy

**Principle:** Cache expensive operations, invalidate on writes.

### What to Cache

| Operation | TTL | Invalidation |
|-----------|-----|--------------|
| LLM responses | 1 hour | Content change |
| Style embeddings | Until song edit | Song update |
| User preferences | 5 min | Preference change |
| Song list | 1 min | Any song CRUD |

### Implementation
```python
# api/services/cache.py

from redis import asyncio as aioredis

class CacheService:
    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl: int = 300,
    ) -> T:
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)

        value = await factory()
        await self.redis.setex(key, ttl, json.dumps(value))
        return value

    async def invalidate(self, pattern: str):
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)


# Usage
class SongService:
    async def list_songs(self, user_id: UUID) -> list[Song]:
        return await self.cache.get_or_set(
            f"songs:user:{user_id}",
            lambda: self._fetch_songs(user_id),
            ttl=60,
        )

    async def create(self, ...) -> Song:
        song = await self._create_song(...)
        await self.cache.invalidate(f"songs:user:{song.user_id}")
        return song
```

---

## 6. Event System

**Principle:** Decouple components with domain events.

### When to Use
- Side effects that shouldn't block the main operation
- Multiple listeners need to react to one event
- Future extensibility (add listeners without changing emitter)

### Implementation
```python
# api/events.py

from typing import Callable, Awaitable

EventHandler = Callable[[dict], Awaitable[None]]

class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event: str):
        def decorator(handler: EventHandler):
            self._handlers.setdefault(event, []).append(handler)
            return handler
        return decorator

    async def publish(self, event: str, **payload):
        for handler in self._handlers.get(event, []):
            await handler(payload)


events = EventBus()


# Define handlers
@events.subscribe("song.created")
async def index_in_style_library(payload: dict):
    await style_library.index_song(payload["song_id"])


@events.subscribe("song.created")
async def notify_user(payload: dict):
    await notifications.send(payload["user_id"], "Song created!")


# Emit events
class SongService:
    async def create(self, ...) -> Song:
        song = await self._create_song(...)
        await events.publish("song.created", song_id=song.id, user_id=song.user_id)
        return song
```

---

## 7. Configuration Management

**Principle:** Centralize configuration with validation.

### App-Specific Config
```python
# api/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Auth
    jwt_secret_key: str
    access_token_expire_minutes: int = 15

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = "mistral"
    openrouter_api_key: str = ""

    # Songwriter-specific
    max_sections_per_song: int = 50
    max_songs_per_user: int = 500
    enable_ai_suggestions: bool = True
    style_library_chunk_size: int = 500

    # Feature flags
    enable_demo_generation: bool = False
    enable_audio_analysis: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()
```

### Usage
```python
# Don't scatter env reads
if os.getenv("ENABLE_AI_SUGGESTIONS", "true").lower() == "true":  # Bad

# Use typed settings
if settings.enable_ai_suggestions:  # Good
    ...
```

---

## 8. Testing Patterns

### Fixtures
```python
# tests/conftest.py

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session


@pytest.fixture
def user(session) -> User:
    user = User(email="test@example.com")
    session.add(user)
    return user
```

### Factories
```python
# tests/factories.py

from faker import Faker

fake = Faker()


class SongFactory:
    @staticmethod
    def build(**kwargs) -> dict:
        return {
            "title": kwargs.get("title", fake.sentence(3)),
            "key": kwargs.get("key", "C"),
            "tempo": kwargs.get("tempo", 120),
        }

    @staticmethod
    async def create(session: AsyncSession, user: User, **kwargs) -> Song:
        song = Song(user_id=user.id, **SongFactory.build(**kwargs))
        session.add(song)
        await session.commit()
        return song
```

### Service Tests
```python
# tests/services/test_song_service.py

async def test_create_song(session, user, mock_style_library):
    service = SongService(session, mock_style_library)

    song = await service.create(
        CreateSongRequest(title="Test Song"),
        user,
    )

    assert song.title == "Test Song"
    assert song.user_id == user.id
    mock_style_library.index_song.assert_called_once_with(song)
```

---

## 9. API Versioning

**Principle:** Plan for breaking changes from the start.

### URL Versioning
```python
# api/routes/__init__.py

from fastapi import APIRouter

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(songs.router)
v1_router.include_router(auth.router)

# Future
v2_router = APIRouter(prefix="/v2")
```

### When to Version
- Breaking changes to request/response schemas
- Removed endpoints
- Changed authentication requirements

### When NOT to Version
- Adding new optional fields
- Adding new endpoints
- Bug fixes

---

## 10. Database Migrations

### Naming Convention
```
XXX_verb_noun_description.py

001_create_users_table.py
002_create_songs_table.py
003_add_tempo_to_songs.py
004_create_style_embeddings_table.py
```

### Safe Migration Patterns
```python
# Adding a column (safe)
op.add_column('songs', sa.Column('tempo', sa.Integer, nullable=True))

# Adding NOT NULL column (needs default or backfill)
op.add_column('songs', sa.Column('status', sa.String, server_default='draft'))
op.alter_column('songs', 'status', server_default=None)

# Renaming (use batch for SQLite compatibility)
with op.batch_alter_table('songs') as batch_op:
    batch_op.alter_column('old_name', new_column_name='new_name')
```

---

## Priority Implementation Order

| Priority | Pattern | Why |
|----------|---------|-----|
| 1 | Service layer | Foundation for everything else |
| 2 | Domain exceptions | Better error handling |
| 3 | Background jobs for AI | UX requirement |
| 4 | Dependency injection | Clean, testable code |
| 5 | Configuration management | Reduce bugs |
| 6 | Testing patterns | Catch regressions |
| 7 | Caching | Performance |
| 8 | Event system | Extensibility |
| 9 | API versioning | Future-proofing |

---

## Checklist for New Features

- [ ] Business logic in service, not route
- [ ] Domain exceptions, not HTTPException in services
- [ ] Dependencies injected via `Depends()`
- [ ] AI operations are background jobs
- [ ] Configuration in `settings`, not scattered `os.getenv()`
- [ ] Tests for service layer
- [ ] Cache invalidation if applicable
- [ ] Events emitted if side effects needed
