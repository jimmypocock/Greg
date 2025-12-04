# Greg Enhancement Roadmap

## Vision

Transform Greg from a local RAG experiment into a production-ready document intelligence platform with:
- Multiple LLM provider support (Ollama, Claude, OpenAI, Gemini)
- Quantitative evaluation metrics
- Cloud deployment capability
- Advanced retrieval techniques

This is also a **learning project** - each phase teaches Deep Learning concepts through hands-on implementation.

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Document Processing | Done | PDF, TXT, MD, images via unified processor |
| Embeddings | Done | Sentence Transformers with memory-safe implementation |
| Vector Store | Done | FAISS with LangChain integration |
| Local LLMs | Done | Ollama integration (Mistral, Llama, Phi, Deepseek) |
| API LLM Providers | Built | Claude, OpenAI, Gemini providers in `src/llm/` |
| FastAPI Backend | Done | Full REST API |
| CLI Interface | Done | Interactive chat and commands |
| Testing | Partial | Needs cleanup and expansion |

---

## Phase Overview

| Phase | Focus | Status | Outcome |
|-------|-------|--------|---------|
| **Phase 0** | Cleanup & Organization | In Progress | Clean, testable codebase |
| **Phase 1** | LLM Integration Testing | Pending | Verified multi-provider support |
| **Phase 2** | Evaluation Framework | Pending | Quantitative quality metrics |
| **Phase 3** | Cloud Deployment | Pending | Shareable demo |
| **Phase 4** | Advanced RAG | Pending | Hybrid search, tutor features |

---

## Learning Goals

By completing this project, you should be able to:

### Embeddings & Vector Search
- Explain why cosine similarity works for comparing embeddings
- Describe tradeoffs between embedding dimensions (384 vs 768)
- Explain when to use IndexFlatIP vs IndexIVFFlat
- Calculate and interpret similarity scores

### RAG Architecture
- Draw the complete RAG pipeline from document to answer
- Explain why chunking matters and how chunk size affects results
- Describe the difference between retrieval and generation
- Implement hybrid search and explain when it helps

### Evaluation
- Define MRR, Recall@K, and Precision@K
- Create an evaluation dataset from scratch
- Interpret evaluation results and identify failure modes
- Compare two RAG systems quantitatively

### Production Considerations
- Implement cost tracking for API calls
- Choose between local and API LLMs based on requirements
- Deploy a RAG system to the cloud
- Handle errors gracefully with fallbacks

---

## File Structure

Each phase has its own detailed document:

```
docs/roadmap/
├── OVERVIEW.md           # This file
├── PHASE_0_CLEANUP.md    # Codebase cleanup and organization
├── PHASE_1_LLM_TESTING.md    # LLM provider testing
├── PHASE_2_EVALUATION.md     # Retrieval metrics
├── PHASE_3_DEPLOYMENT.md     # Cloud deployment
└── PHASE_4_ADVANCED_RAG.md   # Hybrid search, tutor features
```

---

## Next Step

→ See **PHASE_0_CLEANUP.md** for current cleanup tasks.
