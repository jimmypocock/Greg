# Phase 0: Codebase Cleanup & Organization

## Overview

**Goal:** Clean up the codebase, remove unused code, organize files, and establish a solid foundation for future development.

**Status:** In Progress

**Why This Matters:** A clean codebase is easier to understand, test, and extend. This phase sets the stage for everything that follows.

---

## Completed Tasks

- [x] Removed unused Streamlit UI code (`src/ui/`)
- [x] Removed old visual regression tests
- [x] Cleaned up test scripts
- [x] Removed legacy Makefile (replaced with pyproject.toml + uv)
- [x] Removed old requirements.txt (using uv)
- [x] Created unified run.py entry point
- [x] Built LLM provider abstraction layer (`src/llm/`)

---

## In Progress

- [ ] Delete unused scripts in `scripts/` folder
  - Keep: `preprocess_documents.py` (used by run.py)
  - Delete: `list_testable_models.py` (unused utility)
  - Delete: `preprocess_test_documents.py` (orphaned)

- [ ] Create roadmap documentation structure
  - `docs/roadmap/OVERVIEW.md`
  - Phase files for each development stage

- [ ] Review and update CLAUDE.md to reflect current state

---

## Remaining Tasks

- [ ] Audit `src/` modules for unused code
- [ ] Verify all imports are valid after cleanup
- [ ] Run full test suite and fix failures
- [ ] Update .gitignore for new structure
- [ ] Ensure `make run` still works correctly

---

## File Structure After Cleanup

```
Greg/
├── cli.py              # CLI interface
├── main.py             # FastAPI backend
├── run.py              # Unified entry point
├── pyproject.toml      # Dependencies and config
├── uv.lock             # Locked dependencies
├── CLAUDE.md           # AI assistant instructions
│
├── docs/
│   └── roadmap/        # Development roadmap
│
├── documents/          # User documents (gitignored)
│
├── scripts/
│   └── preprocess_documents.py  # Document preprocessing
│
├── src/
│   ├── llm/            # LLM provider abstraction
│   ├── performance/    # Performance monitoring
│   ├── streaming/      # Streaming response handling
│   ├── utils/          # Utility functions
│   └── *.py            # Core modules
│
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   ├── api/            # API tests
│   └── fixtures/       # Test data
│
├── uploads/            # Temporary file storage
└── vector_stores/      # FAISS indexes
```

---

## Success Criteria

- [ ] No unused files in repository
- [ ] All tests pass
- [ ] `make run` works correctly
- [ ] Documentation reflects current state
- [ ] Clean git status (only intentional changes)

---

## Next Phase

→ After cleanup, proceed to **PHASE_1_LLM_TESTING.md** to verify LLM integrations.
