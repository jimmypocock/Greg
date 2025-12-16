# Greg Evaluation Framework

A framework for testing and measuring Greg's RAG performance.

## Quick Start

### 1. Prepare Test Document

Extract chapters 1-2 from the fastai book (or use any PDF you know well):
- Should be 30-50 pages
- Content you understand deeply
- Creates ~20-40 chunks at 800 char size

### 2. Upload to Greg

```bash
# Start Greg
uv run greg dev

# Upload your test PDF (via API or UI)
curl -X POST http://localhost:8080/documents \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@fastai_chapters_1_2.pdf" \
  -F "chunk_size=800"
```

### 3. Note the Document ID

After upload, you'll get a document ID. Use this to target evaluation.

### 4. Run Evaluation

```bash
# Set credentials
export GREG_EMAIL="your-email@example.com"
export GREG_PASSWORD="your-password"

# Run evaluation
python -m tests.evaluation.eval_runner

# Or with specific document
python -m tests.evaluation.eval_runner --document-id <uuid>

# Save results
python -m tests.evaluation.eval_runner --save
```

## Test Case Format

Edit `test_cases.json` to add your own questions:

```json
{
  "id": "unique_id",
  "question": "What is X?",
  "expected_keywords": ["word1", "word2"],
  "expected_not_contain": ["wrong_word"],
  "category": "factual",
  "chapter": 1,
  "notes": "Why this test matters"
}
```

### Categories

| Category | Description | Pass Criteria |
|----------|-------------|---------------|
| `factual` | Who/What/When questions | ≥50% keywords found |
| `conceptual` | Why/How explanations | ≥50% keywords found |
| `unanswerable` | Not in documents | Should indicate uncertainty |
| `multi-doc` | Requires multiple sources | ≥50% keywords found |

## Understanding Results

```
EVALUATION REPORT
==============================================================

Overall: 8/10 (80.0%)
Average retrieval score: 0.723

By Category:
  factual: 4/5 (80%)
  conceptual: 3/4 (75%)
  unanswerable: 1/1 (100%)

--------------------------------------------------------------
FAILED CASES:
--------------------------------------------------------------

[sgd_001] What does SGD stand for and what does it do?
  Missing keywords: ['stochastic', 'batch']
  Answer preview: SGD is gradient descent, a method for updating weights...
```

### Metrics

| Metric | What it measures |
|--------|------------------|
| **Pass rate** | % of test cases passing |
| **Retrieval score** | Average similarity of retrieved chunks (0-1) |
| **Keywords found** | Expected terms in answer |
| **Keywords missing** | Expected terms NOT in answer |

## Iteration Workflow

```
1. Run evaluation → establish baseline
2. Make a change (chunking, retrieval, prompt)
3. Run evaluation again
4. Compare: Did metrics improve?
5. Keep or revert change
6. Repeat
```

## Adding Test Cases

Write tests for content you KNOW:

1. Read the document yourself
2. Write questions you'd actually ask
3. Note the correct answer (keywords)
4. Include edge cases (unanswerable questions)

Good test cases:
- Cover different question types
- Have clear expected answers
- Include "trick" questions (not in docs)
- Target known weaknesses
