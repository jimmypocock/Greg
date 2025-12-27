# Browser-Based ML with JAX-JS

> **Status:** Research / Future Consideration
> **Priority:** Low (nice-to-have optimization)
> **Technology:** [JAX-JS](https://github.com/nicholaswmin/jax-js) - Pure JavaScript ML library

## Overview

JAX-JS is a browser-based reimplementation of Google's JAX framework. It enables running lightweight machine learning models directly in the user's browser using WebGPU and WebAssembly, eliminating the need for server round-trips on certain tasks.

## How It Works

```
User Input → JavaScript → Symbolic Trace → Compiled Kernels → WebGPU/WASM → Result
```

### Key Technologies

| Technology | Purpose | Performance |
|------------|---------|-------------|
| **WebGPU** | GPU-accelerated matrix operations | Near-native GPU speed |
| **WebAssembly** | CPU fallback when GPU unavailable | 10-20x faster than JS |
| **JIT Compilation** | Fuse operations into optimized kernels | Reduces memory transfers |

### Constraints

- **Model size limit:** ~50-100MB practical maximum (browser memory)
- **No large language models:** Can't run GPT-scale models
- **Training:** Only feasible for small models (demos, fine-tuning)
- **Best for:** Inference on pre-trained lightweight models

## When to Use Browser ML vs Server ML

### Use Browser ML (JAX-JS)

- Real-time feedback as user types (< 50ms latency needed)
- Privacy-sensitive classification (content never leaves device)
- Offline functionality required
- High-frequency calls (would overwhelm API rate limits)
- Simple classification/scoring tasks

### Use Server ML (Ollama/OpenAI/Anthropic)

- Text generation (lyrics, suggestions, critiques)
- Complex reasoning or multi-step analysis
- Large context windows needed
- Model quality is critical
- Tasks requiring latest/largest models

## Potential Implementations for Songwriter App

### 1. Rhyme Quality Scoring

**Task:** Rate how well two words/phrases rhyme (0-100 score)

**Why browser?** Called frequently as user types, needs instant feedback

**Implementation:**
```typescript
// Pseudocode
const rhymeModel = await loadModel('rhyme-scorer.onnx');

function scoreRhyme(word1: string, word2: string): number {
  const embedding1 = rhymeModel.embed(word1);
  const embedding2 = rhymeModel.embed(word2);
  return cosineSimilarity(embedding1, embedding2) * 100;
}

// Usage in editor
onWordComplete((word) => {
  const lineEndWords = getPreviousLineEndings();
  const scores = lineEndWords.map(w => ({
    word: w,
    score: scoreRhyme(word, w)
  }));
  showRhymeIndicator(scores);
});
```

**Model:** Small phonetic embedding model (~5-10MB)

---

### 2. Line Similarity Search

**Task:** Find similar lines the user has written across all their songs

**Why browser?** Instant search without API calls, works offline

**Implementation:**
```typescript
// On song load, embed all lines
const lineEmbeddings = new Map<string, Float32Array>();

async function indexSong(song: Song) {
  for (const section of song.sections) {
    for (const line of section.lines) {
      const embedding = await embedModel.encode(line.text);
      lineEmbeddings.set(line.id, embedding);
    }
  }
}

// Search for similar lines
function findSimilarLines(query: string, topK = 5): SimilarLine[] {
  const queryEmbed = embedModel.encode(query);

  return [...lineEmbeddings.entries()]
    .map(([id, embed]) => ({
      id,
      score: cosineSimilarity(queryEmbed, embed)
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, topK);
}
```

**Model:** MiniLM or similar small embedding model (~30MB)

---

### 3. Syllable & Stress Prediction

**Task:** Predict syllable count and stress pattern for words/lines

**Why browser?** Essential for meter feedback, needs real-time response

**Implementation:**
```typescript
interface SyllableInfo {
  count: number;
  pattern: ('S' | 'U')[]; // Stressed / Unstressed
}

function analyzeMeter(line: string): SyllableInfo[] {
  const words = tokenize(line);
  return words.map(word => ({
    word,
    ...syllableModel.predict(word)
  }));
}

// Visual feedback
function renderMeterGuide(line: string) {
  const analysis = analyzeMeter(line);
  // Show: "da-DUM da-DUM da-DUM" pattern
  // Highlight stressed syllables
}
```

**Model:** Small sequence model (~5MB)

---

### 4. Mood/Emotion Classifier

**Task:** Classify emotional tone of lyrics (happy, sad, angry, hopeful, etc.)

**Why browser?** Auto-tag sections as user writes, no API needed

**Implementation:**
```typescript
type Mood = 'happy' | 'sad' | 'angry' | 'hopeful' | 'nostalgic' | 'romantic';

interface MoodScore {
  mood: Mood;
  confidence: number;
}

function classifyMood(text: string): MoodScore[] {
  const scores = moodModel.predict(text);
  return Object.entries(scores)
    .map(([mood, confidence]) => ({ mood, confidence }))
    .sort((a, b) => b.confidence - a.confidence);
}

// Auto-tag sections
function onSectionBlur(section: Section) {
  const moods = classifyMood(section.lyrics);
  section.autoTags = moods.filter(m => m.confidence > 0.6);
}
```

**Model:** Fine-tuned sentiment classifier (~20MB)

---

### 5. Profanity/Content Filter

**Task:** Flag potentially explicit content for user awareness

**Why browser?** Privacy - lyrics never sent to server for checking

**Implementation:**
```typescript
interface ContentFlag {
  type: 'profanity' | 'explicit' | 'sensitive';
  severity: 'mild' | 'moderate' | 'strong';
  span: [number, number]; // Character positions
}

function scanContent(text: string): ContentFlag[] {
  return contentModel.detect(text);
}

// Non-blocking check as user types
const debouncedScan = debounce((text) => {
  const flags = scanContent(text);
  if (flags.length > 0) {
    showContentWarning(flags);
  }
}, 500);
```

**Model:** Small classification model (~10MB)

---

### 6. Chord Progression Similarity

**Task:** Find songs with similar chord progressions

**Why browser?** Quick lookup in user's song library

**Implementation:**
```typescript
// Encode chord progressions as vectors
function encodeProgression(chords: string[]): Float32Array {
  // Convert: ['Am', 'F', 'C', 'G'] → embedding
  return chordModel.encode(chords.join(' '));
}

// Find similar progressions
function findSimilarProgressions(
  targetChords: string[],
  songLibrary: Song[]
): SimilarSong[] {
  const targetEmbed = encodeProgression(targetChords);

  return songLibrary
    .flatMap(song => song.sections.map(s => ({
      song,
      section: s,
      similarity: cosineSimilarity(targetEmbed, s.chordEmbedding)
    })))
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 10);
}
```

**Model:** Custom chord embedding model (~5MB)

---

## Architecture

### Model Loading Strategy

```typescript
// Lazy load models on first use
const modelCache = new Map<string, Model>();

async function getModel(name: string): Promise<Model> {
  if (!modelCache.has(name)) {
    const model = await loadModel(`/models/${name}.onnx`);
    modelCache.set(name, model);
  }
  return modelCache.get(name)!;
}

// Preload critical models after app load
async function preloadModels() {
  await Promise.all([
    getModel('syllable'),
    getModel('rhyme'),
  ]);
}
```

### Web Worker Isolation

Run models in a Web Worker to avoid blocking the UI:

```typescript
// main.ts
const mlWorker = new Worker('/workers/ml-worker.js');

function classifyMood(text: string): Promise<MoodScore[]> {
  return new Promise((resolve) => {
    const id = crypto.randomUUID();
    mlWorker.postMessage({ id, task: 'mood', text });

    const handler = (e: MessageEvent) => {
      if (e.data.id === id) {
        mlWorker.removeEventListener('message', handler);
        resolve(e.data.result);
      }
    };
    mlWorker.addEventListener('message', handler);
  });
}

// ml-worker.js
self.onmessage = async (e) => {
  const { id, task, text } = e.data;
  const model = await getModel(task);
  const result = model.predict(text);
  self.postMessage({ id, result });
};
```

### Storage & Caching

```typescript
// Cache embeddings in IndexedDB
const embeddingStore = new IndexedDBStore('embeddings');

async function getOrComputeEmbedding(
  text: string,
  model: EmbeddingModel
): Promise<Float32Array> {
  const hash = await sha256(text);

  const cached = await embeddingStore.get(hash);
  if (cached) return cached;

  const embedding = await model.encode(text);
  await embeddingStore.set(hash, embedding);
  return embedding;
}
```

---

## Model Sources

### Pre-trained Models to Consider

| Model | Size | Task | Source |
|-------|------|------|--------|
| all-MiniLM-L6-v2 | 23MB | Text embeddings | HuggingFace |
| Silero VAD | 2MB | Voice activity | Silero |
| Whisper Tiny | 40MB | Speech-to-text | OpenAI |
| Custom phonetic | ~5MB | Rhyme scoring | Train ourselves |

### Model Format

Convert models to ONNX format for browser compatibility:

```bash
# Python conversion example
from transformers import AutoModel
import torch

model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
torch.onnx.export(model, dummy_input, "miniLM.onnx")
```

---

## Implementation Phases

### Phase 1: Foundation
- Set up JAX-JS or ONNX Runtime Web
- Create Web Worker infrastructure
- Implement model loading/caching

### Phase 2: Text Embeddings
- Integrate MiniLM for line similarity
- Build search UI for "find similar lines"
- Cache embeddings in IndexedDB

### Phase 3: Syllable Analysis
- Train or find syllable/stress model
- Real-time meter visualization
- Integration with line editor

### Phase 4: Classification
- Mood/emotion classifier
- Auto-tagging for sections
- Content filtering (optional)

### Phase 5: Audio (Future)
- Voice activity detection for recordings
- Basic pitch detection
- Tempo estimation

---

## Performance Considerations

### Bundle Size
- Keep total model size under 50MB
- Lazy load models not needed at startup
- Use CDN for model files (cache-friendly)

### Memory
- Unload unused models after timeout
- Limit concurrent model instances
- Monitor memory usage in dev tools

### Battery/CPU
- Debounce real-time analysis
- Skip analysis when tab not visible
- Provide "low power mode" toggle

---

## Alternatives to JAX-JS

| Library | Pros | Cons |
|---------|------|------|
| **ONNX Runtime Web** | Industry standard, wide model support | Larger bundle |
| **TensorFlow.js** | Google-backed, mature | Heavy, complex |
| **Transformers.js** | HuggingFace models, easy | Limited to supported models |
| **JAX-JS** | Lightweight, JAX-compatible | Newer, less ecosystem |

**Recommendation:** Start with **Transformers.js** for ease of use, consider JAX-JS for custom lightweight models.

---

## Success Metrics

- Reduced API calls for classification tasks
- Sub-100ms response time for real-time features
- Works offline after initial model load
- No noticeable UI jank during inference

---

## References

- [JAX-JS GitHub](https://github.com/nicholaswmin/jax-js)
- [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/)
- [Transformers.js](https://huggingface.co/docs/transformers.js)
- [WebGPU Specification](https://www.w3.org/TR/webgpu/)
