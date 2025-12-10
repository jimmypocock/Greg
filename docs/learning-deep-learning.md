# Learning Deep Learning with Greg

A practical roadmap for understanding ML pipelines through building.

## Your Goals

1. **Understand deep learning fundamentals** - not just use pre-trained models
2. **Build employable skills** - real experience with training, fine-tuning, deployment
3. **Create practical projects** - things that actually work and solve problems

### Project Ideas You're Exploring

| Project | Core ML Technique | Why It's Interesting |
|---------|-------------------|----------------------|
| **Greg (Document Q&A)** | RAG, embeddings, fine-tuning | Full pipeline, enterprise-relevant |
| **Video Scene Analyzer** | Multimodal (Gemini), video understanding | Cutting-edge, creative applications |
| **Songwriting Assistant** | LLM fine-tuning, creative generation | Domain-specific fine-tuning |
| **Startup Doc Analyst** | Classification, NER, structured extraction | Practical business value |

---

## What You Learned: Embeddings Deep Dive

### The Core Concept

An **embedding** is a vector (1D array of numbers) that captures semantic meaning.

```
"The cat sat on the mat" → [0.23, -0.45, 0.12, ..., 0.67]  # 384 numbers
```

### The Full Pipeline

```
Text → Tokenizer → Token IDs → Token Embeddings → Transformer → Pooling → Final Embedding
```

| Step | What Happens | Example |
|------|--------------|---------|
| **Tokenization** | Split text into subwords | "unhappiness" → ["un", "happiness"] |
| **Token IDs** | Lookup in vocabulary table | ["un", "happiness"] → [4521, 8923] |
| **Token Embeddings** | Each ID gets initial vector | 4521 → [0.1, 0.2, ...] (384 dims) |
| **Transformer** | Tokens attend to each other, vectors update with context | Each token now "knows" the full sentence |
| **Pooling** | Combine all token vectors into one | Mean of all vectors → single 384D embedding |

### Key Insights

**Tokenizer vs Model:**
- Tokenizer = dumb lookup table (no understanding)
- Model = learned weights that create meaning
- They're tied together - can't mix different models' components

**Where the "understanding" lives:**
- NOT in the tokenizer
- IN the transformer weights (millions of parameters learned during training)
- Cat/kitten are similar because the model saw them in similar contexts billions of times

**BERT-style vs GPT-style:**

```
BERT:  "The cat sat on the mat"
       ←←←←←←←←←←←→→→→→→→→→→  (bidirectional - all tokens see each other)

GPT:   "The cat sat on the mat"
       → → → → → →  (left-to-right - can only see what came before)
```

- **BERT-style**: Better for understanding/search (embeddings)
- **GPT-style**: Required for generation (can't peek at unwritten words)
- **Greg uses both**: BERT for retrieval, GPT for answering

**What gets stored:**
- Only the final pooled embedding (384D vector) goes into pgvector
- Intermediate tensors are temporary computation
- Matrices/tensors are for batching and GPU parallelism, not storage

**Cosine similarity scores:**
- 0.9+ = Nearly identical
- 0.7-0.9 = Very similar
- 0.5-0.7 = Related
- 0.3-0.5 = Loosely related
- <0.3 = Different topics

**UMAP vs Mean Pooling:**
- Mean pooling: Combines multiple vectors into one (same dimensions)
- UMAP: Reduces dimensions for visualization (384D → 2D, lossy)
- UMAP is only for debugging/visualization - production uses full vectors

---

## Model Architecture & Training

### Pre-trained Models

You'll almost always start with pre-trained models. Training from scratch requires:
- Billions of text samples
- Massive GPU clusters
- Months of training time
- Millions of dollars

### Ways to Customize

| Approach | What Changes | Cost | Use Case |
|----------|--------------|------|----------|
| **Prompt engineering** | Nothing (just better prompts) | Free | First thing to try |
| **RAG** | Add retrieval, no model changes | Low | What Greg does now |
| **Fine-tuning** | Adjust existing weights | Medium | Domain adaptation |
| **Custom head** | Add new layers on top | Medium | New output format |
| **LoRA adapters** | Small trainable patches | Low-Medium | Per-customer models |
| **Train from scratch** | Everything | Very High | Almost never needed |

### Fine-tuning vs Custom Head

**Fine-tuning:** Adjust existing weights throughout the model
- Risk: Catastrophic forgetting (gets better at your domain, worse at general)
- Mitigation: LoRA keeps original weights frozen

**Custom head:** Add new layer(s) on top, freeze base model
- Example: Take 384D embedding → add layer → output 5 class probabilities
- Faster to train, less risk

### LoRA (Low-Rank Adaptation)

Lightweight fine-tuning that doesn't destroy original weights:

```
Original: Input → [22M weights] → Output

LoRA:     Input → [22M weights (frozen)] → Output
                         ↓
                  [~100K adapter weights (trainable)]
```

- Adapter is 0.1-1% of model size
- Can have different adapters per customer
- Merge at inference time

**What you need:**
- GPU: Colab free tier works
- Training data: 100-1000 example pairs
- Storage: ~10-50MB per adapter
- Libraries: HuggingFace PEFT

### Online APIs vs Local Models

| Aspect | Online (OpenAI, Anthropic, Google) | Local (Ollama, HuggingFace) |
|--------|-------------------------------------|------------------------------|
| **Layer access** | None - black box | Full control |
| **Fine-tuning** | Limited (example pairs only) | Full (LoRA, custom heads) |
| **Cost** | Per-request | Upfront (GPU) then free |
| **Deployment** | Their infra | Your responsibility |
| **Privacy** | Data leaves your system | Stays local |

**For Greg:** Use both
- Online LLMs for generation (quality, no GPU needed)
- Local embeddings for retrieval (free, customizable, private)
- You CAN mix: local embeddings + OpenAI for answers

**You don't need OpenAI embeddings** unless:
- You want their specific quality/dimensions
- You're comparing against their embedding space
- Local models aren't good enough for your domain

---

## Chunking Strategies

| Method | How It Works | Tradeoff |
|--------|--------------|----------|
| **Character-based** (current) | Split at ~800 chars | Fast, dumb |
| **Token-based** | Split at ~200 tokens | More accurate for LLM context |
| **Sentence-based** | Split on . ! ? then group | Preserves meaning better |
| **Semantic chunking** | Use embeddings to find topic boundaries | Slower, smarter |

This is a good optimization target once you have evaluation metrics.

---

## Different Data Types

| Data Type | Model Architecture | How Embeddings Work |
|-----------|-------------------|---------------------|
| **Text** | Transformer (BERT/GPT) | Tokens → vectors → pool |
| **Images** | Vision Transformer, CLIP | Patches → vectors → pool |
| **Audio** | Whisper, Wav2Vec | Waveform → spectrograms → vectors |
| **Video** | Gemini, video models | Frames + audio → combined understanding |
| **Multimodal** | CLIP, Gemini | Text AND images in same vector space |

For your video project: Gemini can process video natively - frames, audio, and generate text about scenes.

---

## Learning Roadmap

### Phase 1: Embeddings Deep Dive (DONE)
- [x] Understand what embeddings are
- [x] Tokenization → transformer → pooling pipeline
- [x] Cosine similarity and what scores mean
- [x] BERT vs GPT style training
- [x] Visualize with UMAP

### Phase 2: Evaluation Framework (NEXT)
Build the ability to measure if Greg is working well.

**Notebook 2: Evaluation Framework**
```
1. Create test dataset
   - 10 documents you know well
   - 20 questions with known good answers
   - Label which chunks should be retrieved

2. Measure retrieval quality
   - Does Greg find the right chunks?
   - Precision@k, Recall@k, MRR

3. Measure answer quality
   - Are answers correct?
   - Do they use the retrieved context?

4. Establish baseline metrics
   - This becomes your benchmark for experiments
```

### Phase 3: Chunking Experiments
With evaluation in place, experiment with chunking.

**Notebook 3: Smarter Chunking**
```
1. Implement different chunking strategies
2. Measure retrieval quality for each
3. Find what works best for your doc types
```

### Phase 4: Fine-tuning Embeddings
Make retrieval better for your specific domain.

**Notebook 4: LoRA Fine-tuning**
```
1. Create training pairs (similar/dissimilar chunks)
2. Fine-tune embedding model with LoRA
3. Compare retrieval quality: base vs fine-tuned
4. Deploy and test in Greg
```

### Phase 5: Classification & NER
Add document intelligence.

**Notebook 5: Document Classification**
```
1. Generate synthetic startup docs (or collect real ones)
2. Label document types (term sheet, pitch deck, etc.)
3. Train classifier (custom head on embedding model)
4. Add auto-categorization to Greg
```

### Phase 6: LLM Fine-tuning (Advanced)
Domain-specific answer generation.

**Notebook 6: Answer Quality**
```
1. Collect good Q&A pairs from your domain
2. Fine-tune small LLM with LoRA
3. Compare: base model vs fine-tuned
4. Understand when fine-tuning helps
```

---

## Deployment Thinking

### Current Greg Architecture
```
User → FastAPI → [Embedding Model] → pgvector → [LLM] → Response
                  (local or API)                (API)
```

### With Local Fine-tuned Model
```
Train locally (Colab/your GPU)
       ↓
Save weights (~500MB-2GB) or adapter (~10-50MB)
       ↓
Upload to S3/HuggingFace
       ↓
Production server downloads once, serves inference
```

### Cost-Effective Deployment

| Component | Budget Option | Better Option |
|-----------|---------------|---------------|
| **Embeddings** | CPU inference ($5/mo VPS) | GPU inference (~$0.50/hr) |
| **Vector DB** | pgvector (already have) | pgvector (scales well) |
| **LLM** | Ollama on same box | API calls (OpenAI/Anthropic) |
| **Fine-tuned adapters** | S3 storage (~$0.02/GB) | HuggingFace Hub (free) |

---

## Key Takeaways

1. **Tokenizer = lookup, Model = understanding** - The semantic magic is in the transformer weights, not the tokenizer.

2. **You almost never train from scratch** - Pre-trained models + fine-tuning is the practical path.

3. **LoRA is your friend** - Lightweight fine-tuning without destroying the base model.

4. **Evaluation before optimization** - Build metrics first, then you can measure if changes help.

5. **Mix and match** - Local embeddings + cloud LLMs is a valid architecture. Use what makes sense.

6. **Start with the pipeline, optimize later** - Greg already works. Now measure, then improve.

---

## Next Session

Start with **Notebook 2: Evaluation Framework**. This is the foundation for everything else - you can't improve what you can't measure.

We'll:
1. Create a test dataset from documents you know
2. Write questions with expected answers
3. Build retrieval quality metrics
4. Establish your baseline

Once you can measure, chunking experiments, fine-tuning, and other optimizations become scientific rather than guesswork.
