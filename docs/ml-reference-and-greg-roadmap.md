# ML Reference & Greg Improvement Roadmap

A reference guide for ML architectures and a roadmap for improving Greg.

---

## Standard ML Architectures by Task

| Task                 | Architecture                  | Notes                        |
|----------------------|-------------------------------|------------------------------|
| Image classification | ResNet, EfficientNet, ViT     | CNNs or Vision Transformers  |
| Object detection     | YOLO, Faster R-CNN            | Find objects + locations     |
| Text generation      | Transformer (GPT-style)       | Decoder-only                 |
| Text understanding   | BERT, RoBERTa                 | Encoder-only                 |
| Translation          | Transformer (encoder-decoder) | Original design              |
| Speech               | Whisper, Wav2Vec              | Audio → text                 |
| Image generation     | U-Net + Diffusion             | Stable Diffusion             |
| Tabular data         | Simple MLPs, XGBoost          | Deep learning often overkill |

---

## Typical ML Workflow (2025)

1. Pick standard architecture for your task
2. Find pre-trained version (HuggingFace, PyTorch Hub, etc.)
3. Adapt output layer to your problem
4. Fine-tune on your data
5. Done

Training from scratch is rare now - you're usually building on proven architectures with pre-trained weights.

---

## Greg Assessment

### What Greg Does Well

| Strength           | Why it matters                           |
|--------------------|------------------------------------------|
| Clean architecture | Modular, maintainable, proper separation |
| Auth system        | Production-ready user management         |
| Background jobs    | Async processing, won't block on uploads |
| Cost tracking      | Know what you're spending                |
| Local LLM option   | Privacy, cost control                    |
| Proper API design  | RESTful, documented, testable            |

**Summary:** Real infrastructure, not a toy.

---

### Where Greg Falls Short

#### 1. Chunking is probably naive

```python
# What you likely have
chunks = split_by_size(document, 500)  # Fixed size

# What loses context
"The CEO said profits increased."  # Chunk 1
"He also mentioned layoffs."       # Chunk 2 - who is "He"?
```

**Problem:** Semantic boundaries ignored, context lost across chunks.

#### 2. No evaluation framework

You can't answer:
- "Are my answers actually good?"
- "Did this change make things better or worse?"
- "What types of questions fail?"

**This is the biggest gap.** You're flying blind.

#### 3. Retrieval is probably too simple

```python
# What you likely have
results = vector_search(query_embedding, top_k=5)

# What's missing
# - Hybrid search (vector + keyword BM25)
# - Re-ranking retrieved chunks
# - Query expansion ("startup funding" → also search "venture capital", "seed round")
```

#### 4. No hallucination guardrails

Does Greg:
- Know when it doesn't know?
- Cite which chunks it used?
- Refuse to answer if retrieval is poor?

#### 5. Document structure ignored

```
Original document:
  # Chapter 3: Revenue
  ## Q2 Results
  Table: [revenue by region]

After chunking:
  Just flat text, structure lost
```

Headers, sections, tables, relationships - probably all flattened.

#### 6. No multi-hop reasoning

Question: "Compare the CEO's stance in the 2022 report vs 2023 report"

This requires:
- Finding 2022 content
- Finding 2023 content
- Synthesizing across both

Simple RAG struggles here.

#### 7. No confidence signals

User gets an answer but doesn't know:
- How confident is the system?
- Which documents supported this?
- Were there conflicting sources?

---

## Improvement Roadmap

### Priority 1: Evaluation Framework (FIRST)

Build this before changing anything else:

```python
test_cases = [
    {"question": "What was Q2 revenue?", "expected": "4.2M", "source_doc": "q2_report.pdf"},
    {"question": "Who is the CEO?", "expected": "Jane Smith", "source_doc": "about.pdf"},
]

def evaluate(rag_system, test_cases):
    results = []
    for case in test_cases:
        answer = rag_system.ask(case["question"])
        results.append({
            "correct": case["expected"] in answer,
            "retrieved_right_doc": case["source_doc"] in answer.sources,
        })
    return results
```

**Without this, every other improvement is guesswork.**

### Priority 2: Retrieval Quality

```python
# Add hybrid search
vector_results = pgvector_search(query)
keyword_results = postgres_fulltext_search(query)
combined = reciprocal_rank_fusion(vector_results, keyword_results)

# Add re-ranking
reranked = cross_encoder_rerank(query, combined[:20])
final = reranked[:5]
```

### Priority 3: Chunking Strategy

- Chunk by semantic boundaries (paragraphs, sections)
- Overlap chunks (last 2 sentences of chunk N = first 2 of chunk N+1)
- Store parent-child relationships (chunk belongs to section X)

### Priority 4: Answer Quality

```python
# Cite sources
answer = f"{generated_text}\n\nSources:\n- {doc1.name}, page {chunk1.page}\n- {doc2.name}, page {chunk2.page}"

# Add confidence
if max_similarity < 0.7:
    answer = "I don't have enough information to answer this confidently."
```

---

## Quick Wins vs Deep Work

| Quick Win (days)              | Deep Work (weeks)    |
|-------------------------------|----------------------|
| Add source citations          | Evaluation framework |
| Chunk overlap                 | Hybrid search        |
| Confidence threshold          | Smarter chunking     |
| Show retrieved chunks to user | Re-ranking pipeline  |

---

## Recommended Timeline

### Week 1-2: Build evaluation framework
- 20-50 test questions with expected answers
- Automated scoring
- Run before/after any change

### Week 3-4: Improve retrieval
- Hybrid search
- Test with your evaluation framework
- Measure improvement

### Week 5+: Iterate on whatever evaluation shows is weakest

---

## RAG Evaluation Metrics

| Metric               | Question it answers                                    |
|----------------------|--------------------------------------------------------|
| Retrieval quality    | Did we find the right chunks?                          |
| Answer correctness   | Is the answer factually right?                         |
| Faithfulness         | Is the answer grounded in retrieved docs (not hallucinated)? |
| Answer completeness  | Did we miss important information?                     |

---

## Test Case Categories

```python
categories = {
    "factual": "Who/What/When questions with clear answers",
    "how-to": "Process questions, step-by-step",
    "comparison": "Compare X vs Y",
    "summary": "Summarize this document/section",
    "multi-doc": "Answer requires info from multiple documents",
    "unanswerable": "Question that docs DON'T cover (should say 'I don't know')",
}
```

The **unanswerable** category is critical - tests if Greg knows when it doesn't know.
