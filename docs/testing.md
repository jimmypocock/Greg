# Testing Strategy for Greg

A practical testing approach for a solo developer pre-production.

## Current State

Existing test infrastructure:
```
tests/
├── conftest.py      # Shared fixtures (outdated - no auth)
├── api/             # API endpoint tests
├── unit/            # Unit tests
├── integration/     # Integration tests
└── fixtures/        # Test data files
```

**Problem:** Existing tests don't handle authentication (added recently). They need updating.

## Testing Philosophy

For a solo dev pre-production:

1. **Test the critical path** - Don't test everything, test what breaks
2. **Catch regressions** - Tests for bugs you've fixed
3. **Fast feedback** - Tests should run in seconds, not minutes
4. **Minimal mocking** - Use a real test database when practical

## Priority 1: API Smoke Tests

These catch 80% of issues. Test each endpoint returns expected status codes.

### What to Test

| Endpoint | Method | Auth | Test |
|----------|--------|------|------|
| `/health` | GET | None | Returns 200, status="healthy" |
| `/auth/register` | POST | None | Returns 201 (first user) |
| `/auth/token` | POST | None | Returns tokens |
| `/auth/me` | GET | JWT | Returns user info |
| `/documents` | GET | JWT | Returns document list |
| `/documents` | POST | JWT | Returns job_id |
| `/ask` | POST | JWT | Returns SSE stream |
| `/web-search` | POST | JWT | Returns SSE stream |

### Example: Auth-Aware Test Fixture

```python
# tests/conftest.py - Updated for auth

import pytest
import httpx
from typing import Generator

API_URL = "http://localhost:8080"

@pytest.fixture(scope="session")
def test_user_credentials():
    """Test user credentials."""
    return {
        "email": "test@example.com",
        "password": "testpassword123"
    }

@pytest.fixture(scope="session")
def auth_token(test_user_credentials) -> str:
    """Get auth token, registering user if needed."""
    # Try to login first
    response = httpx.post(
        f"{API_URL}/auth/token",
        json=test_user_credentials,
        timeout=10
    )

    if response.status_code == 200:
        return response.json()["access_token"]

    # Register if login failed
    response = httpx.post(
        f"{API_URL}/auth/register",
        json={
            **test_user_credentials,
            "invite_code": None  # First user doesn't need invite
        },
        timeout=10
    )

    if response.status_code == 201:
        # Login after registration
        response = httpx.post(
            f"{API_URL}/auth/token",
            json=test_user_credentials,
            timeout=10
        )
        return response.json()["access_token"]

    pytest.fail(f"Could not get auth token: {response.text}")

@pytest.fixture
def auth_headers(auth_token) -> dict:
    """Headers with auth token."""
    return {"Authorization": f"Bearer {auth_token}"}
```

### Example: Smoke Tests

```python
# tests/api/test_smoke.py

import pytest
import httpx

API_URL = "http://localhost:8080"

class TestPublicEndpoints:
    """Test endpoints that don't require auth."""

    def test_health(self):
        response = httpx.get(f"{API_URL}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_models(self):
        response = httpx.get(f"{API_URL}/models")
        assert response.status_code == 200


class TestAuthenticatedEndpoints:
    """Test endpoints that require auth."""

    def test_documents_list(self, auth_headers):
        response = httpx.get(
            f"{API_URL}/documents",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "documents" in response.json()

    def test_documents_requires_auth(self):
        response = httpx.get(f"{API_URL}/documents")
        assert response.status_code == 401

    def test_ask_requires_auth(self):
        response = httpx.post(
            f"{API_URL}/ask",
            json={"question": "test"}
        )
        assert response.status_code == 401
```

## Priority 2: Regression Tests

When you fix a bug, write a test to ensure it doesn't come back.

### Bugs Fixed Recently (Add Tests For These)

```python
# tests/regression/test_bug_fixes.py

def test_document_id_defaults_to_all():
    """Bug: document_id was required, should default to 'all'."""
    # Previously returned 422 without document_id
    response = httpx.post(
        f"{API_URL}/ask",
        json={"question": "test question"},
        headers=auth_headers
    )
    # Should work without document_id
    assert response.status_code == 200

def test_batch_chunk_indexing():
    """Bug: Chunks in batch 2+ got wrong indices (restarted at 0)."""
    # Upload a document large enough to require multiple batches
    # Verify all chunks have unique (document_id, chunk_index)
    pass

def test_embedding_provider_enum_lowercase():
    """Bug: Enum sent 'OPENAI' but DB expected 'openai'."""
    # Upload with OpenAI embeddings
    # Verify document processes successfully
    pass

def test_openai_max_completion_tokens():
    """Bug: OpenAI newer models require max_completion_tokens not max_tokens."""
    # Ask a question using OpenAI provider
    # Verify no 400 error about unsupported parameter
    pass

def test_web_search_not_awaited():
    """Bug: Async generator was incorrectly awaited."""
    response = httpx.post(
        f"{API_URL}/web-search",
        json={"question": "test"},
        headers=auth_headers
    )
    assert response.status_code == 200
```

## Priority 3: Unit Tests for Complex Logic

Only unit test code with complex logic or many edge cases.

### Worth Unit Testing

- `src/config/validation.py` - Required var validation
- `src/vectorstore/pgvector_store.py` - Chunk indexing logic
- `src/auth/refresh_tokens.py` - Token rotation logic
- `src/documents/service.py` - File type detection

### Not Worth Unit Testing

- Simple CRUD routes
- Thin wrapper functions
- Code that just calls external APIs

### Example: Config Validation Unit Test

```python
# tests/unit/test_config.py

import os
import pytest
from src.config.validation import get_required, ConfigurationError

def test_get_required_returns_value():
    os.environ["TEST_VAR"] = "test_value"
    assert get_required("TEST_VAR") == "test_value"
    del os.environ["TEST_VAR"]

def test_get_required_raises_on_missing():
    with pytest.raises(ConfigurationError):
        get_required("NONEXISTENT_VAR_12345")

def test_get_required_raises_on_empty():
    os.environ["TEST_VAR"] = "   "
    with pytest.raises(ConfigurationError):
        get_required("TEST_VAR")
    del os.environ["TEST_VAR"]
```

## Running Tests

```bash
# Run all tests
uv run greg test

# Run specific test file
uv run greg test tests/api/test_smoke.py

# Run tests matching pattern
uv run greg test -k "auth"

# Run with verbose output
uv run greg test -v

# Run only fast tests (skip slow/integration)
uv run greg test -m "not slow"
```

## Test Database Strategy

**Option A: Use dev database (simpler)**
- Tests run against your dev database
- Clean up test data after each test
- Risk: Could corrupt dev data if cleanup fails

**Option B: Separate test database (safer)**
- Set `DATABASE_URL` to a test database in test env
- Can wipe entire database between test runs
- Requires docker-compose override or env switching

For now, Option A is fine pre-production. Add cleanup fixtures:

```python
@pytest.fixture
def cleanup_test_documents(auth_headers):
    """Track and cleanup documents created during tests."""
    created_ids = []

    yield created_ids  # Test adds IDs to this list

    # Cleanup
    for doc_id in created_ids:
        httpx.delete(
            f"{API_URL}/documents/{doc_id}",
            headers=auth_headers
        )
```

## What NOT to Test

1. **Third-party libraries** - OpenAI SDK, SQLAlchemy, FastAPI
2. **Simple getters/setters** - No logic to test
3. **Private methods** - Test through public interface
4. **Logging statements** - Not worth the effort
5. **100% coverage** - Diminishing returns after ~70%

## CI/CD (Later)

When you're ready for production:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run greg test
```

## Summary

| Priority | What | Why | When |
|----------|------|-----|------|
| 1 | Smoke tests | Catch broken endpoints | Now |
| 2 | Regression tests | Prevent bug recurrence | After each bug fix |
| 3 | Unit tests | Complex logic | When logic is tricky |
| 4 | Integration tests | Full workflows | Pre-production |
| 5 | CI/CD | Automated checks | Production |

Start with Priority 1 and 2. Add others as needed.
