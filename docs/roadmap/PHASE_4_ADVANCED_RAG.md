# Phase 4: Advanced RAG Features

## Overview

**Goal:** Add hybrid search and tutor features to make Greg a compelling portfolio piece.

**Status:** Pending

**Why This Matters:**
- Hybrid search often beats pure semantic search
- Tutor features show you can build beyond basic RAG
- These are features interviewers find impressive

---

## Part 1: Hybrid Search

### Why Hybrid?

Semantic and keyword search have complementary strengths:

| Query Type | Semantic Wins | Keyword Wins |
|------------|---------------|--------------|
| "How do I fix errors?" | Understands intent | Misses "debugging" |
| "error code 404" | Might miss exact match | Finds exact "404" |
| "PostgreSQL version 15" | Might miss version | Exact match |

**Hybrid search combines both** using weighted scoring.

### Implementation

```
Combined Score = α × Semantic Score + (1-α) × Keyword Score
```

Where α = 0.7 means 70% semantic, 30% keyword (recommended starting point).

### Tasks

- [ ] Add BM25 for keyword search (`rank-bm25` library)
- [ ] Create HybridSearcher class
- [ ] Implement score normalization
- [ ] Add alpha tuning via evaluation
- [ ] Integrate with QA chain

---

## Part 2: Tutor Features

### Feature 1: Quiz Generation

Generate quiz questions from documents to test understanding.

```python
class QuizGenerator:
    def generate_quiz(
        self,
        chunks: List[Dict],
        topic: str,
        num_questions: int = 5,
        difficulty: str = "medium"
    ) -> Quiz
```

### Feature 2: Concept Explainer

Explain concepts at different detail levels:
- **Brief**: 2-3 sentences
- **Standard**: Explanation + example
- **Detailed**: Comprehensive with analogies

### Feature 3: Answer Evaluator

Evaluate user answers and provide feedback:
- Correctness score (0-10)
- Completeness score (0-10)
- Missing points
- Improvement suggestions

---

## Module Structure

```
src/
├── search/
│   ├── __init__.py
│   └── hybrid.py       # Hybrid search implementation
│
└── tutor/
    ├── __init__.py
    ├── quiz.py         # Quiz generation
    ├── explain.py      # Concept explanation
    └── evaluate.py     # Answer evaluation
```

---

## Measuring Impact

After implementing hybrid search, compare against baseline:

```python
# Baseline: semantic only (alpha=1.0)
baseline = evaluate(search_func, alpha=1.0)

# Hybrid: 70% semantic + 30% keyword
hybrid = evaluate(search_func, alpha=0.7)

print(f"MRR improvement: {(hybrid.mrr - baseline.mrr) / baseline.mrr * 100:.1f}%")
```

---

## Learning Objectives

After completing this phase, you should understand:

- Difference between semantic and keyword search
- When hybrid search outperforms pure semantic
- How to tune the alpha parameter
- How to generate educational content with LLMs
- How to evaluate open-ended answers

---

## Success Criteria

- [ ] Hybrid search implemented and working
- [ ] Evaluated optimal alpha for your documents
- [ ] Quiz generation produces sensible questions
- [ ] Concept explainer works at all detail levels
- [ ] Answer evaluator gives useful feedback
- [ ] Evaluation shows improvement with hybrid search

---

## Project Complete!

After Phase 4, Greg has evolved from a local experiment into a production-ready document Q&A system with:

- Multiple LLM provider support
- Cost tracking
- Quantitative evaluation metrics
- Cloud deployment
- Hybrid search
- Tutor features

This represents a complete, portfolio-ready RAG implementation.
