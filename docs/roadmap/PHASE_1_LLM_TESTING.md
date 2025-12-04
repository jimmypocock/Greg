# Phase 1: LLM Integration Testing

## Overview

**Goal:** Verify that all LLM providers work correctly and integrate properly with Greg's RAG pipeline.

**Status:** Pending

**Why This Matters:** The LLM provider abstraction layer is built, but needs thorough testing to ensure reliability and proper error handling.

---

## Current State

The `src/llm/` module contains:

| File | Purpose |
|------|---------|
| `base.py` | Abstract base class for providers |
| `factory.py` | Factory for creating providers |
| `ollama_provider.py` | Local Ollama integration |
| `anthropic_provider.py` | Claude API |
| `openai_provider.py` | OpenAI API |
| `google_provider.py` | Gemini API |

---

## Tasks

### 1. Provider Testing

- [ ] Test Ollama provider
  - [ ] Basic generation
  - [ ] Streaming generation
  - [ ] Model switching
  - [ ] Error handling (Ollama not running)

- [ ] Test Anthropic (Claude) provider
  - [ ] Basic generation
  - [ ] Streaming generation
  - [ ] Token counting
  - [ ] Cost calculation
  - [ ] Error handling (invalid key, rate limits)

- [ ] Test OpenAI provider
  - [ ] Basic generation
  - [ ] Streaming generation
  - [ ] Token counting
  - [ ] Cost calculation
  - [ ] Error handling

- [ ] Test Google (Gemini) provider
  - [ ] Basic generation
  - [ ] Streaming generation
  - [ ] Token counting
  - [ ] Cost calculation
  - [ ] Error handling

### 2. Integration Testing

- [ ] Provider switching via environment variables
- [ ] Provider switching via API/CLI
- [ ] Fallback behavior when primary provider fails
- [ ] Integration with QA chain
- [ ] Streaming responses through FastAPI

### 3. Cost Tracking

- [ ] Implement cost tracking per query
- [ ] Persist cost data across sessions
- [ ] Add cost display to CLI
- [ ] Add cost endpoint to API

---

## Test Scripts

Create test scripts to verify each provider:

```bash
# Test with Ollama (free, local)
LLM_PROVIDER=ollama python -c "
from src.llm import get_llm_provider
llm = get_llm_provider()
response = llm.generate('What is 2+2?')
print(f'Response: {response.content}')
print(f'Tokens: {response.total_tokens}')
"

# Test with Claude (requires ANTHROPIC_API_KEY)
LLM_PROVIDER=anthropic python -c "
from src.llm import get_llm_provider
llm = get_llm_provider()
response = llm.generate('What is 2+2?')
print(f'Response: {response.content}')
print(f'Cost: \${response.cost_usd:.4f}')
"
```

---

## Environment Configuration

Update `.env` to support provider selection:

```bash
# LLM Provider (ollama, anthropic, openai, google)
LLM_PROVIDER=ollama

# Default model per provider
LLM_MODEL=mistral

# API Keys (only needed for respective providers)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=

# Cost limits
DAILY_COST_LIMIT_USD=5.00
```

---

## Learning Objectives

After completing this phase, you should understand:

- How to abstract LLM providers behind a common interface
- The difference between local and API LLMs (quality vs cost vs privacy)
- How to calculate API costs (input tokens × rate + output tokens × rate)
- Why fallback strategies matter for reliability

---

## Success Criteria

- [ ] All four providers work correctly
- [ ] Can switch providers via environment variable
- [ ] Streaming works for all providers
- [ ] Cost tracking is functional
- [ ] Error handling is graceful (no crashes)
- [ ] Integration tests pass

---

## Next Phase

→ After verifying LLM integrations, proceed to **PHASE_2_EVALUATION.md** to add quality metrics.
