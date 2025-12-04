# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Greg is a local AI playground featuring a Retrieval-Augmented Generation (RAG) system with a RESTful API:

1. **Ollama Service** (port 11434): Runs local LLMs (Mistral, Llama, Phi, Deepseek)
2. **FastAPI Backend** (port 8080): Handles document processing, vector storage, and Q&A logic
3. **CLI Interface**: Command-line interface for interactive chat and document management
4. **Document Preprocessing**: Automatic processing of documents in `/documents` folder at startup

## Critical: How to Work with This Project

### 1. ALWAYS Use Make Commands
This project uses a Makefile for ALL operations. Never run Python commands directly.

### 2. Virtual Environment
The virtual environment is managed automatically by the Makefile and scripts. You do NOT need to:
- Manually activate venv
- Run pip install

Everything is handled by `make install` and the startup scripts.

### 3. Document Management
Documents can be managed two ways:
- **Filesystem**: Place documents in the `/documents` folder and run `make run`
- **API Upload**: Use `POST /upload` or `python cli.py upload <file>` at runtime

### 4. Starting the Application
```bash
# Start API with document preprocessing (recommended):
make run

# This automatically:
# - Checks/installs dependencies
# - Starts Ollama
# - Starts API server
# - Clears vector stores
# - Processes all documents in /documents folder

# Start API server only (no preprocessing):
make api

# Start interactive CLI (requires API running):
make cli
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health and memory stats |
| `/models` | GET | List available LLM models |
| `/documents` | GET | List processed documents |
| `/upload` | POST | Upload and process a document |
| `/ask` | POST | Ask a question (streaming) |
| `/ask-streaming` | POST | Explicit streaming endpoint |
| `/web-search` | POST | Search the web |
| `/process-url` | POST | Process a URL as a document |
| `/documents/{id}` | DELETE | Delete a document |
| `/clear-all` | POST | Clear all documents |
| `/storage-stats` | GET | Vector store statistics |
| `/docs` | GET | OpenAPI documentation |

## CLI Commands

```bash
# Interactive chat mode (default)
python cli.py

# Ask a question
python cli.py ask "What is this document about?"

# Ask with web search
python cli.py ask "What is the weather?" --web

# Web search only
python cli.py search "latest AI news"

# Upload a document
python cli.py upload document.pdf

# List documents
python cli.py docs

# List models
python cli.py models

# Check API health
python cli.py health

# Interactive chat commands:
#   /web      - Toggle web search mode
#   /upload   - Upload a document
#   /model    - Switch model
#   /models   - List models
#   /docs     - List documents
#   /help     - Show help
#   exit      - Quit
```

## Testing the Application

### Testing Strategy
Greg uses a streamlined testing approach:

1. **Unit Tests** - Fast tests including security validations
2. **API Tests** - Comprehensive backend coverage
3. **Integration Tests** - Service interaction tests
4. **Performance Tests** - Optimization and caching tests

### Quick Test Commands
```bash
# Run all tests (recommended)
make test

# Quick tests for development
make test-quick        # Unit tests only

# Individual test suites
make test-unit         # Unit tests (includes security)
make test-api          # API endpoint tests
make test-integration  # Integration tests
make test-performance  # Performance tests

# Model testing
make test-models       # Test specific models
make test-models-quick # Quick compatibility test
```

### Test Infrastructure
- **Test Runner**: Simplified test runner in `tests/run_tests.py`
- **Fixtures**: Test files in `tests/fixtures/`
- **Security Tests**: Included in unit tests

### Common Test Issues & Solutions

1. **Port Conflicts**:
   - Tests check if services are already running before starting new instances
   - No need to stop `make run` before testing

2. **Import Errors**:
   - All imports should use `from src.module` format
   - Never use relative imports in tests

3. **Model Tests**:
   - Require models to be downloaded first
   - Use `make test-models MODELS='mistral'` to test specific models

## Important Make Commands

### Development
- `make run` - Start API with document preprocessing
- `make api` - Start API server only
- `make cli` - Start interactive CLI
- `make clean` - Clean temporary files
- `make monitor` - Monitor resources
- `make models` - List available models

### Testing
- `make test` - Run all tests
- `make test-quick` - Quick unit tests
- `make test-unit` - Unit tests
- `make test-api` - API endpoint tests
- `make test-integration` - Integration tests
- `make test-performance` - Performance tests
- `make test-models MODELS='mistral,llama3'` - Test specific models

## Architecture Details

### Data Flow
1. Documents placed in `/documents` folder OR uploaded via API
2. On startup: preprocessing script -> unified document processor -> chunks -> embeddings -> FAISS vector store
3. User queries -> Query classification (6 intent types) -> UnifiedQAChain routes query -> FAISS similarity search -> context retrieval -> Ollama LLM -> streaming response
4. Web search queries -> Direct to LLM with web context
5. All documents stored in single vector store with source metadata

### Query Classification System
The app uses intelligent pattern-based classification to route queries:
- **DOCUMENT_QUESTION**: Default for document queries
- **ANALYSIS_REQUEST**: Compare, summarize, analyze
- **DATA_EXTRACTION**: Extract specific data
- **COMPUTATION**: Math and calculations
- **CASUAL_CHAT**: Greetings (skips document loading)
- **WEB_SEARCH**: Current events (searches web)

### File Structure
```
/
├── documents/            # Place your documents here (gitignored)
│   └── README.md        # Instructions for users
├── scripts/              # Utility scripts
│   └── preprocess_documents.py  # Document preprocessing
├── src/                  # Core application code
│   ├── performance/     # Performance monitoring
│   ├── streaming/       # Streaming response handling
│   └── *.py            # Core modules
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   ├── api/            # API tests
│   ├── performance/    # Performance tests
│   ├── results/        # Test output files (gitignored)
│   └── fixtures/       # Test data
├── vector_stores/      # FAISS indexes (cleared on startup)
├── uploads/            # Temporary file storage
├── cli.py             # CLI interface
├── main.py            # FastAPI backend
├── run.sh             # Startup script
└── Makefile           # All commands
```

### Key Modules
- `src/config.py`: Environment configuration and memory optimization
- `src/unified_document_processor.py`: Multi-document processing into single vector store
- `src/qa_chain_unified.py`: Unified QA chain with intelligent routing and streaming
- `src/memory_safe_embeddings.py`: Memory-efficient embeddings with caching
- `src/web_search.py`: Web search functionality
- `src/security.py`: Input sanitization and validation

### Vector Store Persistence
- Single unified store saved in `vector_stores/unified_store.faiss`
- Metadata in `unified_store_metadata.json`
- All documents indexed in one store with source attribution
- Cleared and rebuilt on each startup for consistency

### Error Handling Best Practices
- Connection errors show helpful messages
- Processing timeouts: 300s for large files
- Memory monitoring prevents OOM
- All errors logged with context

## CORS Configuration

For deployment, configure CORS via environment variables:

```bash
# Allow specific origins (comma-separated)
export ALLOWED_ORIGINS="https://myapp.com,https://api.myapp.com"

# Or allow all origins (development only)
export CORS_ALLOW_ALL=true
```

Default development origins:
- `http://localhost:3000` (NextJS)
- `http://localhost:5173` (Vite)
- `http://localhost:8080` (API docs)

## Model Compatibility

### Known Issues
- **Deepseek**: Requires minimal parameters (only `num_ctx`)
- Some models don't support `num_thread`, `repeat_penalty`, or custom `stop` tokens
- Model config stored in `src/model_config.json`

### Testing Models
```bash
# Test all models
make test-models

# Test specific models
make test-models MODELS='deepseek,mistral'

# Quick format compatibility test
make test-models-quick
```

## Best Practices

### When Making Changes
1. Run `make run` to start the API
2. Make changes to code
3. Test with `make test` or specific test commands
4. Run `make test` before committing

### Common Pitfalls to Avoid
- Don't manually manage venv - use make commands
- Don't skip tests - all must pass
- Don't use relative imports - use `from src.module`
- Don't hardcode ports - use config values

### Debugging Tips
- Check service status with `make monitor`
- Logs available in terminal output
- API docs at `http://localhost:8080/docs`
- Use `--verbose` flag for detailed test output

## Quick Reference

```bash
# Start API
make run

# Interactive CLI
python cli.py

# Ask a question
python cli.py ask "What is this about?"

# Upload a document
python cli.py upload myfile.pdf

# Run all tests
make test

# Check what's running
make monitor
```

## Future: Adding LLM Providers

The `/models` endpoint is designed to be extensible. To add new providers:

1. Set environment variables:
   - `OPENAI_API_KEY` for OpenAI
   - `ANTHROPIC_API_KEY` for Anthropic
   - `GOOGLE_API_KEY` for Google/Gemini

2. The `/models` endpoint will automatically list available models from configured providers.

3. Use the `model_name` parameter in `/ask` requests to specify which model to use:
   ```json
   {
     "question": "What is this about?",
     "document_id": "unified",
     "model_name": "gpt-4"
   }
   ```
