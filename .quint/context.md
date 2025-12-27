# Bounded Context

## Vocabulary

- **Greg**: Modular creative writing platform serving as foundation for multiple apps. Songwriter
- **App**: Primary application for AI-assisted songwriting with collaborative features.
- **Song**: Musical composition containing sections, lyrics, chord progressions, and metadata.
- **Section**: Structural part of a song (verse, chorus, bridge, intro, outro).
- **Agent**: Specialized AI assistant with distinct role and personality (songwriter, producer, critic, coach, manager). Critic
- **Agent**: AI providing constructive feedback and evaluation on songs. Producer
- **Agent**: AI advising on chords, arrangement, dynamics, and sonic choices. Coach
- **Agent**: AI for skill development, exercises, and learning paths. Manager
- **Agent**: AI for career planning, releases, and goal tracking. Multi-Agent
- **Orchestration**: System where multiple agents collaborate and hand off tasks. Tool
- **Binding**: Exposing app functions as callable tools for AI agents. Data-to-
- **Text**: Converting structured data to prose for LLM prompts.
- **OpenRouter**: Unified API gateway for multiple LLM providers. Browser
- **ML**: Client-side machine learning via JAX-JS or similar for low-latency tasks.

## Invariants

Must use PostgreSQL with pgvector for vector embeddings. FastAPI backend with async Python. Authentication via JWT access tokens (15min) + refresh tokens (7 days). Modular architecture: api/ for backend, web/ for Next.js frontend. Background jobs via Redis + ARQ worker. Local LLM inference via Ollama for development. Cloud LLM via direct APIs or OpenRouter for production. WebSocket for real-time progress updates. Pydantic for request/response validation. First user becomes admin automatically. Rate limiting on auth endpoints. No over-engineering: build only what's needed now. Decisions must be documented with rationale.
