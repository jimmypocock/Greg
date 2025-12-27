<explanation>

# Building an Efficient RAG System: A Comprehensive Implementation Guide

## Overview

A RAG system transforms static documents into a dynamic knowledge base that an LLM can query intelligently. The core pipeline flows through: **Ingestion → Chunking → Embedding → Indexing → Retrieval → Generation**. Each stage has significant impact on final output quality, and the decisions compound—poor chunking undermines even the best retrieval strategy.

---

## 1. Document Ingestion and Preprocessing

### Handling Multiple File Formats

Different formats require different extraction strategies. The goal is clean, structured text with preserved semantic meaning.

**PDF Documents**

```python
# PyMuPDF (fitz) for most PDFs - fast and reliable
import fitz

def extract_pdf_text(path: str) -> list[dict]:
    doc = fitz.open(path)
    pages = []
    for page_num, page in enumerate(doc):
        text = page.get_text("text")
        # Preserve structure with blocks for better chunking later
        blocks = page.get_text("dict")["blocks"]
        pages.append({
            "page": page_num + 1,
            "text": text,
            "blocks": blocks  # Contains position info for citations
        })
    return pages
```

For scanned/image-based PDFs, use OCR:

```python
# pdfplumber + pytesseract for OCR
import pdfplumber
from PIL import Image
import pytesseract

def extract_scanned_pdf(path: str) -> str:
    with pdfplumber.open(path) as pdf:
        text_parts = []
        for page in pdf.pages:
            # Try text extraction first
            text = page.extract_text()
            if not text or len(text.strip()) < 50:
                # Fall back to OCR
                img = page.to_image(resolution=300).original
                text = pytesseract.image_to_string(img)
            text_parts.append(text)
    return "\n\n".join(text_parts)
```

**Word Documents (DOCX)**

```python
from docx import Document

def extract_docx(path: str) -> dict:
    doc = Document(path)
    content = {
        "paragraphs": [p.text for p in doc.paragraphs if p.text.strip()],
        "tables": [],
        "headers": []
    }
    
    # Extract tables separately for structured data
    for table in doc.tables:
        table_data = []
        for row in table.rows:
            table_data.append([cell.text for cell in row.cells])
        content["tables"].append(table_data)
    
    # Track heading styles for structure-aware chunking
    for para in doc.paragraphs:
        if para.style.name.startswith('Heading'):
            content["headers"].append({
                "level": int(para.style.name[-1]) if para.style.name[-1].isdigit() else 1,
                "text": para.text
            })
    
    return content
```

**HTML/Web Content**

```python
from bs4 import BeautifulSoup
import html2text

def extract_html(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, nav elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header']):
        element.decompose()
    
    # Convert to markdown for cleaner structure
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = True
    markdown = h.handle(str(soup))
    
    return {
        "text": soup.get_text(separator="\n", strip=True),
        "markdown": markdown,
        "title": soup.title.string if soup.title else None
    }
```

### Preprocessing Best Practices

```python
import re
import unicodedata

def clean_text(text: str) -> str:
    # Normalize unicode characters
    text = unicodedata.normalize("NFKC", text)
    
    # Fix common OCR/extraction artifacts
    text = re.sub(r'(?<=[a-z])-\n(?=[a-z])', '', text)  # Dehyphenate
    text = re.sub(r'\n{3,}', '\n\n', text)  # Normalize paragraph breaks
    text = re.sub(r'[ \t]+', ' ', text)  # Normalize whitespace
    text = re.sub(r'[^\S\n]+', ' ', text)  # Keep newlines, normalize other whitespace
    
    # Remove page numbers, headers/footers (common patterns)
    text = re.sub(r'\n\s*\d+\s*\n', '\n', text)  # Standalone page numbers
    
    return text.strip()

def extract_metadata(path: str) -> dict:
    """Extract document metadata for filtering and citation."""
    import os
    from datetime import datetime
    
    stat = os.stat(path)
    return {
        "filename": os.path.basename(path),
        "filepath": path,
        "file_type": os.path.splitext(path)[1].lower(),
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "size_bytes": stat.st_size
    }
```

---

## 2. Chunking Strategies

Chunking is where most RAG systems succeed or fail. The goal is creating chunks that are **semantically coherent** (complete thoughts), **appropriately sized** (enough context without noise), and **retrievable** (distinct enough to match queries).

### Strategy Comparison

| Strategy | Best For | Chunk Size | Overlap |
|----------|----------|------------|---------|
| Fixed-size | Uniform documents, speed | 512-1024 tokens | 10-20% |
| Recursive | Mixed content | 256-512 tokens | 50-100 tokens |
| Semantic | Technical docs, varied structure | Variable | Sentence boundary |
| Parent-child | High precision needs | Small: 128, Parent: 1024 | By hierarchy |

### Implementation: Recursive Character Splitting

This is the most versatile approach, splitting on natural boundaries while respecting size limits:

```python
from typing import List
import tiktoken

class RecursiveChunker:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",      # Paragraphs
            "\n",        # Lines  
            ". ",        # Sentences
            ", ",        # Clauses
            " ",         # Words
            ""           # Characters (fallback)
        ]
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))
    
    def split_text(self, text: str, separators: List[str] = None) -> List[str]:
        separators = separators or self.separators
        separator = separators[0]
        remaining_separators = separators[1:]
        
        splits = text.split(separator)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for split in splits:
            split_length = self.count_tokens(split)
            
            if split_length > self.chunk_size:
                # Recursively split with next separator
                if remaining_separators:
                    sub_chunks = self.split_text(split, remaining_separators)
                    chunks.extend(sub_chunks)
                else:
                    # Force split at chunk_size if no more separators
                    chunks.append(split[:self.chunk_size])
                continue
            
            if current_length + split_length > self.chunk_size:
                # Finalize current chunk
                chunk_text = separator.join(current_chunk)
                chunks.append(chunk_text)
                
                # Start new chunk with overlap
                overlap_tokens = 0
                overlap_parts = []
                for part in reversed(current_chunk):
                    part_tokens = self.count_tokens(part)
                    if overlap_tokens + part_tokens <= self.chunk_overlap:
                        overlap_parts.insert(0, part)
                        overlap_tokens += part_tokens
                    else:
                        break
                
                current_chunk = overlap_parts + [split]
                current_length = overlap_tokens + split_length
            else:
                current_chunk.append(split)
                current_length += split_length
        
        if current_chunk:
            chunks.append(separator.join(current_chunk))
        
        return chunks
```

### Semantic Chunking

For documents where meaning matters more than size consistency:

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple

class SemanticChunker:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.75,
        min_chunk_size: int = 100,
        max_chunk_size: int = 1000
    ):
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
    
    def split_into_sentences(self, text: str) -> List[str]:
        # Simple sentence splitting; consider using spaCy for production
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def chunk(self, text: str) -> List[str]:
        sentences = self.split_into_sentences(text)
        if not sentences:
            return [text] if text.strip() else []
        
        # Embed all sentences
        embeddings = self.model.encode(sentences)
        
        # Find semantic boundaries
        chunks = []
        current_chunk = [sentences[0]]
        current_embedding = embeddings[0]
        
        for i in range(1, len(sentences)):
            similarity = np.dot(current_embedding, embeddings[i]) / (
                np.linalg.norm(current_embedding) * np.linalg.norm(embeddings[i])
            )
            
            current_text = " ".join(current_chunk)
            
            # Check if we should start a new chunk
            should_split = (
                similarity < self.similarity_threshold and 
                len(current_text) >= self.min_chunk_size
            ) or len(current_text) >= self.max_chunk_size
            
            if should_split:
                chunks.append(current_text)
                current_chunk = [sentences[i]]
                current_embedding = embeddings[i]
            else:
                current_chunk.append(sentences[i])
                # Update embedding as running average
                current_embedding = (current_embedding + embeddings[i]) / 2
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
```

### Parent-Child (Hierarchical) Chunking

This strategy uses small chunks for precise retrieval but returns larger parent chunks for context:

```python
from dataclasses import dataclass
from typing import Optional
import uuid

@dataclass
class Chunk:
    id: str
    text: str
    parent_id: Optional[str]
    metadata: dict

class HierarchicalChunker:
    def __init__(
        self,
        parent_chunk_size: int = 1024,
        child_chunk_size: int = 256,
        child_overlap: int = 50
    ):
        self.parent_size = parent_chunk_size
        self.child_size = child_chunk_size
        self.child_overlap = child_overlap
        self.recursive_chunker = RecursiveChunker(
            chunk_size=child_chunk_size,
            chunk_overlap=child_overlap
        )
    
    def chunk(self, text: str, doc_metadata: dict) -> Tuple[List[Chunk], List[Chunk]]:
        parent_chunks = []
        child_chunks = []
        
        # First, create parent chunks
        parent_chunker = RecursiveChunker(
            chunk_size=self.parent_size,
            chunk_overlap=0  # No overlap for parents
        )
        parent_texts = parent_chunker.split_text(text)
        
        for i, parent_text in enumerate(parent_texts):
            parent_id = str(uuid.uuid4())
            parent_chunk = Chunk(
                id=parent_id,
                text=parent_text,
                parent_id=None,
                metadata={
                    **doc_metadata,
                    "chunk_type": "parent",
                    "chunk_index": i
                }
            )
            parent_chunks.append(parent_chunk)
            
            # Create child chunks within this parent
            child_texts = self.recursive_chunker.split_text(parent_text)
            for j, child_text in enumerate(child_texts):
                child_chunk = Chunk(
                    id=str(uuid.uuid4()),
                    text=child_text,
                    parent_id=parent_id,
                    metadata={
                        **doc_metadata,
                        "chunk_type": "child",
                        "parent_index": i,
                        "child_index": j
                    }
                )
                child_chunks.append(child_chunk)
        
        return parent_chunks, child_chunks
```

### Contextual Chunking (Anthropic's Approach)

Add context to each chunk that explains where it fits in the document:

```python
def add_contextual_headers(chunks: List[str], document_title: str, section_headers: List[str]) -> List[dict]:
    """
    Prepend contextual information to each chunk.
    This dramatically improves retrieval by giving each chunk document-level context.
    """
    contextualized = []
    current_section = None
    
    for i, chunk in enumerate(chunks):
        # Determine which section this chunk belongs to
        # (In practice, track this during chunking)
        
        context_prefix = f"Document: {document_title}\n"
        if current_section:
            context_prefix += f"Section: {current_section}\n"
        context_prefix += f"Chunk {i + 1} of {len(chunks)}\n\n"
        
        contextualized.append({
            "text": chunk,
            "contextualized_text": context_prefix + chunk,
            "context": {
                "document": document_title,
                "section": current_section,
                "position": i / len(chunks)  # Relative position
            }
        })
    
    return contextualized
```

---

## 3. Embedding Generation

### Choosing an Embedding Model

| Model | Dimensions | Context | Speed | Quality | Cost |
|-------|------------|---------|-------|---------|------|
| text-embedding-3-small | 1536 | 8191 | Fast | Good | $0.02/1M |
| text-embedding-3-large | 3072 | 8191 | Medium | Excellent | $0.13/1M |
| all-MiniLM-L6-v2 | 384 | 256 | Very Fast | Good | Free |
| all-mpnet-base-v2 | 768 | 384 | Fast | Very Good | Free |
| nomic-embed-text | 768 | 8192 | Fast | Very Good | Free |
| bge-large-en-v1.5 | 1024 | 512 | Medium | Excellent | Free |

For local deployment with FAISS, **nomic-embed-text** or **bge-large-en-v1.5** offer excellent quality-to-speed ratios.

### Embedding Implementation

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import hashlib

class EmbeddingGenerator:
    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
        batch_size: int = 32,
        normalize: bool = True,
        cache_enabled: bool = True
    ):
        self.model = SentenceTransformer(model_name)
        self.batch_size = batch_size
        self.normalize = normalize
        self.cache = {} if cache_enabled else None
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def _get_cache_key(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()
    
    def embed_texts(self, texts: List[str], show_progress: bool = True) -> np.ndarray:
        """Embed a list of texts, using cache when available."""
        results = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []
        
        # Check cache
        if self.cache is not None:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text)
                if cache_key in self.cache:
                    results[i] = self.cache[cache_key]
                else:
                    texts_to_embed.append(text)
                    indices_to_embed.append(i)
        else:
            texts_to_embed = texts
            indices_to_embed = list(range(len(texts)))
        
        # Embed uncached texts
        if texts_to_embed:
            embeddings = self.model.encode(
                texts_to_embed,
                batch_size=self.batch_size,
                show_progress_bar=show_progress,
                normalize_embeddings=self.normalize
            )
            
            for idx, embedding in zip(indices_to_embed, embeddings):
                results[idx] = embedding
                if self.cache is not None:
                    self.cache[self._get_cache_key(texts[idx])] = embedding
        
        return np.array(results)
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query. Some models use different prefixes for queries."""
        # BGE models benefit from a query prefix
        if "bge" in self.model._model_card_vars.get("name", "").lower():
            query = "Represent this sentence for searching relevant passages: " + query
        
        return self.model.encode(
            query,
            normalize_embeddings=self.normalize
        )
```

### Embedding Best Practices

1. **Normalize embeddings** for cosine similarity (most models do this internally)
2. **Batch processing** significantly speeds up embedding large document sets
3. **Cache embeddings** - they're expensive to compute and deterministic
4. **Use query prefixes** when the model supports them (BGE, E5)
5. **Consider late interaction models** (ColBERT) for highest quality at cost of complexity

---

## 4. Vector Storage and Indexing

### FAISS Implementation (Local)

```python
import faiss
import numpy as np
import pickle
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    metadata: dict

class FAISSVectorStore:
    def __init__(
        self,
        dimension: int,
        index_type: str = "IVF",  # "Flat", "IVF", "HNSW"
        nlist: int = 100,  # Number of clusters for IVF
        m: int = 32,  # HNSW connections per layer
    ):
        self.dimension = dimension
        self.index_type = index_type
        
        if index_type == "Flat":
            # Exact search - best for < 10k vectors
            self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine for normalized)
        elif index_type == "IVF":
            # Approximate search with clustering - good for 10k-1M vectors
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, nlist, faiss.METRIC_INNER_PRODUCT)
            self._needs_training = True
        elif index_type == "HNSW":
            # Graph-based - excellent for 10k-10M vectors
            self.index = faiss.IndexHNSWFlat(dimension, m, faiss.METRIC_INNER_PRODUCT)
            self.index.hnsw.efConstruction = 200  # Higher = better quality, slower build
        
        self.chunks: List[dict] = []  # Store chunk data alongside vectors
        self.id_to_idx: dict = {}
    
    def add(self, embeddings: np.ndarray, chunks: List[dict]):
        """Add vectors and their associated chunk data."""
        if self.index_type == "IVF" and hasattr(self, '_needs_training') and self._needs_training:
            if len(embeddings) >= self.index.nlist:
                self.index.train(embeddings)
                self._needs_training = False
            else:
                # Not enough data to train IVF, fall back to flat
                self.index = faiss.IndexFlatIP(self.dimension)
        
        start_idx = len(self.chunks)
        self.index.add(embeddings.astype('float32'))
        
        for i, chunk in enumerate(chunks):
            self.chunks.append(chunk)
            self.id_to_idx[chunk['id']] = start_idx + i
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_fn: Optional[callable] = None
    ) -> List[SearchResult]:
        """Search for similar vectors, optionally filtering results."""
        # Fetch more results if filtering
        fetch_k = k * 3 if filter_fn else k
        
        if self.index_type == "IVF":
            self.index.nprobe = 10  # Number of clusters to search
        if self.index_type == "HNSW":
            self.index.hnsw.efSearch = max(k * 2, 64)  # Search quality
        
        scores, indices = self.index.search(
            query_embedding.reshape(1, -1).astype('float32'),
            fetch_k
        )
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for missing results
                continue
            
            chunk = self.chunks[idx]
            
            if filter_fn and not filter_fn(chunk):
                continue
            
            results.append(SearchResult(
                chunk_id=chunk['id'],
                text=chunk['text'],
                score=float(score),
                metadata=chunk.get('metadata', {})
            ))
            
            if len(results) >= k:
                break
        
        return results
    
    def save(self, path: str):
        """Persist index and metadata to disk."""
        faiss.write_index(self.index, f"{path}.faiss")
        with open(f"{path}.meta", 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'id_to_idx': self.id_to_idx,
                'dimension': self.dimension,
                'index_type': self.index_type
            }, f)
    
    @classmethod
    def load(cls, path: str) -> 'FAISSVectorStore':
        """Load index and metadata from disk."""
        with open(f"{path}.meta", 'rb') as f:
            meta = pickle.load(f)
        
        store = cls(meta['dimension'], meta['index_type'])
        store.index = faiss.read_index(f"{path}.faiss")
        store.chunks = meta['chunks']
        store.id_to_idx = meta['id_to_idx']
        
        return store
```

### Hybrid Storage with BM25

Combining vector search with keyword search significantly improves retrieval:

```python
from rank_bm25 import BM25Okapi
import numpy as np
from typing import List

class HybridSearch:
    def __init__(self, vector_store: FAISSVectorStore, embedding_generator: EmbeddingGenerator):
        self.vector_store = vector_store
        self.embedder = embedding_generator
        self.bm25 = None
        self.tokenized_corpus = []
    
    def index_documents(self, chunks: List[dict]):
        """Build both vector and BM25 indices."""
        # Vector index
        texts = [c['text'] for c in chunks]
        embeddings = self.embedder.embed_texts(texts)
        self.vector_store.add(embeddings, chunks)
        
        # BM25 index
        self.tokenized_corpus = [self._tokenize(text) for text in texts]
        self.bm25 = BM25Okapi(self.tokenized_corpus)
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization - consider using a proper tokenizer."""
        return text.lower().split()
    
    def search(
        self,
        query: str,
        k: int = 5,
        vector_weight: float = 0.7,
        bm25_weight: float = 0.3
    ) -> List[SearchResult]:
        """Hybrid search combining vector similarity and BM25."""
        # Vector search
        query_embedding = self.embedder.embed_query(query)
        vector_results = self.vector_store.search(query_embedding, k=k*2)
        
        # BM25 search
        tokenized_query = self._tokenize(query)
        bm25_scores = self.bm25.get_scores(tokenized_query)
        
        # Normalize scores
        vector_scores = {r.chunk_id: r.score for r in vector_results}
        max_vector = max(vector_scores.values()) if vector_scores else 1
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1
        
        # Combine scores using Reciprocal Rank Fusion (RRF)
        combined_scores = {}
        
        # Add vector scores
        for i, result in enumerate(vector_results):
            rrf_score = 1 / (60 + i + 1)  # RRF with k=60
            combined_scores[result.chunk_id] = combined_scores.get(result.chunk_id, 0) + vector_weight * rrf_score
        
        # Add BM25 scores
        bm25_ranked = np.argsort(bm25_scores)[::-1][:k*2]
        for rank, idx in enumerate(bm25_ranked):
            chunk_id = self.vector_store.chunks[idx]['id']
            rrf_score = 1 / (60 + rank + 1)
            combined_scores[chunk_id] = combined_scores.get(chunk_id, 0) + bm25_weight * rrf_score
        
        # Sort by combined score and return top k
        sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)[:k]
        
        results = []
        for chunk_id in sorted_ids:
            idx = self.vector_store.id_to_idx[chunk_id]
            chunk = self.vector_store.chunks[idx]
            results.append(SearchResult(
                chunk_id=chunk_id,
                text=chunk['text'],
                score=combined_scores[chunk_id],
                metadata=chunk.get('metadata', {})
            ))
        
        return results
```

---

## 5. Advanced Retrieval Mechanisms

### Query Expansion with HyDE

Hypothetical Document Embedding generates a hypothetical answer, embeds it, then searches:

```python
class HyDERetriever:
    def __init__(
        self,
        vector_store: FAISSVectorStore,
        embedder: EmbeddingGenerator,
        llm_client  # Your LLM client (Anthropic, OpenAI, Ollama)
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.llm = llm_client
    
    def generate_hypothetical_document(self, query: str) -> str:
        """Generate a hypothetical document that would answer the query."""
        prompt = f"""Write a short passage that would directly answer this question. 
Write as if you're certain and knowledgeable, even if you need to make reasonable assumptions.
Keep it factual and informative, 2-3 sentences.

Question: {query}

Passage:"""
        
        response = self.llm.generate(prompt, max_tokens=150)
        return response
    
    def search(self, query: str, k: int = 5) -> List[SearchResult]:
        """Search using the hypothetical document embedding."""
        hypothetical_doc = self.generate_hypothetical_document(query)
        
        # Embed the hypothetical document instead of the query
        hyde_embedding = self.embedder.embed_texts([hypothetical_doc])[0]
        
        return self.vector_store.search(hyde_embedding, k=k)
```

### Multi-Query Retrieval

Generate multiple query variations to capture different aspects:

```python
class MultiQueryRetriever:
    def __init__(self, base_retriever, llm_client):
        self.retriever = base_retriever
        self.llm = llm_client
    
    def generate_queries(self, original_query: str, n: int = 3) -> List[str]:
        """Generate alternative phrasings of the query."""
        prompt = f"""Generate {n} different versions of this search query to help find relevant information.
Each version should capture the same intent but use different words or angles.

Original query: {original_query}

Output each query on a new line, numbered 1-{n}:"""
        
        response = self.llm.generate(prompt, max_tokens=200)
        
        # Parse queries from response
        queries = [original_query]  # Always include original
        for line in response.strip().split('\n'):
            # Remove numbering
            cleaned = line.strip().lstrip('0123456789.-) ')
            if cleaned and cleaned != original_query:
                queries.append(cleaned)
        
        return queries[:n+1]  # Original + n variations
    
    def search(self, query: str, k: int = 5) -> List[SearchResult]:
        """Search with multiple query variations and combine results."""
        queries = self.generate_queries(query)
        
        all_results = {}
        for i, q in enumerate(queries):
            results = self.retriever.search(q, k=k)
            for rank, result in enumerate(results):
                if result.chunk_id not in all_results:
                    all_results[result.chunk_id] = {
                        'result': result,
                        'rrf_score': 0
                    }
                # Reciprocal Rank Fusion
                all_results[result.chunk_id]['rrf_score'] += 1 / (60 + rank + 1)
        
        # Sort by combined RRF score
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )
        
        return [item['result'] for item in sorted_results[:k]]
```

### Reranking with Cross-Encoders

Cross-encoders evaluate query-document pairs jointly for higher accuracy:

```python
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)
    
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 5
    ) -> List[SearchResult]:
        """Rerank results using cross-encoder scores."""
        if not results:
            return []
        
        # Create query-document pairs
        pairs = [[query, result.text] for result in results]
        
        # Score all pairs
        scores = self.model.predict(pairs)
        
        # Sort by cross-encoder score
        scored_results = list(zip(results, scores))
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Update scores and return top k
        reranked = []
        for result, score in scored_results[:top_k]:
            reranked.append(SearchResult(
                chunk_id=result.chunk_id,
                text=result.text,
                score=float(score),  # Now using cross-encoder score
                metadata=result.metadata
            ))
        
        return reranked
```

---

## 6. Context Assembly and Prompt Construction

### Building the Context Window

```python
from typing import List, Optional
import tiktoken

class ContextBuilder:
    def __init__(
        self,
        max_context_tokens: int = 4000,
        model: str = "gpt-4"  # For token counting
    ):
        self.max_tokens = max_context_tokens
        self.tokenizer = tiktoken.encoding_for_model(model)
    
    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))
    
    def build_context(
        self,
        results: List[SearchResult],
        query: str,
        include_metadata: bool = True
    ) -> tuple[str, List[dict]]:
        """
        Assemble retrieved chunks into a context string.
        Returns (context_string, citations_list)
        """
        context_parts = []
        citations = []
        total_tokens = 0
        
        # Sort by relevance score (already sorted from retrieval)
        # But consider position - middle chunks are often missed ("lost in the middle")
        # Interleave high and medium relevance for better attention
        
        for i, result in enumerate(results):
            # Build citation reference
            citation = {
                "index": i + 1,
                "chunk_id": result.chunk_id,
                "source": result.metadata.get("filename", "Unknown"),
                "page": result.metadata.get("page"),
                "section": result.metadata.get("section")
            }
            citations.append(citation)
            
            # Format chunk with citation marker
            if include_metadata:
                source_info = f"[Source {i+1}: {citation['source']}"
                if citation['page']:
                    source_info += f", Page {citation['page']}"
                source_info += "]"
                chunk_text = f"{source_info}\n{result.text}"
            else:
                chunk_text = f"[{i+1}] {result.text}"
            
            chunk_tokens = self.count_tokens(chunk_text)
            
            if total_tokens + chunk_tokens > self.max_tokens:
                # Truncate or skip
                remaining = self.max_tokens - total_tokens
                if remaining > 100:  # Only include if meaningful
                    # Truncate to fit
                    truncated = self.tokenizer.decode(
                        self.tokenizer.encode(chunk_text)[:remaining]
                    )
                    context_parts.append(truncated + "...")
                break
            
            context_parts.append(chunk_text)
            total_tokens += chunk_tokens
        
        context = "\n\n---\n\n".join(context_parts)
        return context, citations
    
    def build_prompt(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> dict:
        """Build the full prompt for the LLM."""
        
        default_system = """You are a helpful assistant that answers questions based on the provided context.

Instructions:
- Answer based ONLY on the information in the context below
- If the context doesn't contain enough information, say so clearly
- Cite your sources using [Source N] notation when making specific claims
- Be concise but thorough"""

        user_prompt = f"""Context:
{context}

---

Question: {query}

Please answer the question based on the context above. Cite sources where appropriate."""

        return {
            "system": system_prompt or default_system,
            "user": user_prompt
        }
```

### Handling Citations

```python
import re
from typing import List, Tuple

def extract_citations(response: str, citations: List[dict]) -> Tuple[str, List[dict]]:
    """
    Extract and resolve citation references from the LLM response.
    Returns (response_with_resolved_citations, used_citations)
    """
    used_indices = set()
    
    # Find all [Source N] or [N] references
    pattern = r'\[(?:Source\s*)?(\d+)\]'
    matches = re.findall(pattern, response)
    
    for match in matches:
        idx = int(match) - 1
        if 0 <= idx < len(citations):
            used_indices.add(idx)
    
    used_citations = [citations[i] for i in sorted(used_indices)]
    
    # Optionally resolve to full citations
    def resolve_citation(match):
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(citations):
            c = citations[idx]
            return f"[{c['source']}" + (f", p.{c['page']}" if c.get('page') else "") + "]"
        return match.group(0)
    
    resolved_response = re.sub(pattern, resolve_citation, response)
    
    return resolved_response, used_citations

def format_citation_footer(citations: List[dict]) -> str:
    """Format citations as a footer/reference list."""
    if not citations:
        return ""
    
    lines = ["\n---\nSources:"]
    for i, c in enumerate(citations, 1):
        line = f"{i}. {c['source']}"
        if c.get('page'):
            line += f", Page {c['page']}"
        if c.get('section'):
            line += f" - {c['section']}"
        lines.append(line)
    
    return "\n".join(lines)
```

---

## 7. Complete RAG Pipeline

Putting it all together:

```python
class RAGPipeline:
    def __init__(
        self,
        embedding_model: str = "BAAI/bge-large-en-v1.5",
        rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        retrieval_k: int = 10,
        rerank_k: int = 5,
        max_context_tokens: int = 4000
    ):
        self.embedder = EmbeddingGenerator(embedding_model)
        self.vector_store = FAISSVectorStore(
            dimension=self.embedder.dimension,
            index_type="HNSW"
        )
        self.hybrid_search = HybridSearch(self.vector_store, self.embedder)
        self.reranker = Reranker(rerank_model)
        self.chunker = RecursiveChunker(chunk_size, chunk_overlap)
        self.context_builder = ContextBuilder(max_context_tokens)
        
        self.retrieval_k = retrieval_k
        self.rerank_k = rerank_k
    
    def ingest_document(self, file_path: str) -> int:
        """Process and index a document. Returns number of chunks created."""
        # Extract text based on file type
        ext = file_path.split('.')[-1].lower()
        
        if ext == 'pdf':
            pages = extract_pdf_text(file_path)
            text = "\n\n".join(p['text'] for p in pages)
        elif ext == 'docx':
            content = extract_docx(file_path)
            text = "\n\n".join(content['paragraphs'])
        elif ext in ['txt', 'md']:
            with open(file_path, 'r') as f:
                text = f.read()
        else:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # Clean and chunk
        text = clean_text(text)
        chunk_texts = self.chunker.split_text(text)
        
        # Create chunk objects with metadata
        metadata = extract_metadata(file_path)
        chunks = []
        for i, chunk_text in enumerate(chunk_texts):
            chunks.append({
                'id': f"{metadata['filename']}_{i}",
                'text': chunk_text,
                'metadata': {
                    **metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunk_texts)
                }
            })
        
        # Index
        self.hybrid_search.index_documents(chunks)
        
        return len(chunks)
    
    def query(
        self,
        question: str,
        use_reranking: bool = True,
        filter_fn: callable = None
    ) -> dict:
        """
        Query the RAG system.
        Returns dict with 'answer', 'citations', 'context_used'
        """
        # Retrieve
        results = self.hybrid_search.search(question, k=self.retrieval_k)
        
        # Filter if provided
        if filter_fn:
            results = [r for r in results if filter_fn(r)]
        
        # Rerank
        if use_reranking and len(results) > self.rerank_k:
            results = self.reranker.rerank(question, results, self.rerank_k)
        
        # Build context
        context, citations = self.context_builder.build_context(results, question)
        prompt = self.context_builder.build_prompt(question, context)
        
        return {
            'prompt': prompt,
            'citations': citations,
            'retrieved_chunks': results
        }
```

---

## 8. Optimization Techniques

### Caching Strategy

```python
import hashlib
import json
from functools import lru_cache

class QueryCache:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []
    
    def _hash_query(self, query: str, filters: dict = None) -> str:
        key_data = {'query': query, 'filters': filters or {}}
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
    
    def get(self, query: str, filters: dict = None):
        key = self._hash_query(query, filters)
        if key in self.cache:
            # Move to end (most recent)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def set(self, query: str, results, filters: dict = None):
        key = self._hash_query(query, filters)
        
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        
        self.cache[key] = results
        self.access_order.append(key)
```

### Metadata Filtering

Pre-filtering by metadata before vector search dramatically improves performance:

```python
def search_with_filters(
    self,
    query: str,
    k: int = 5,
    file_types: List[str] = None,
    date_range: Tuple[str, str] = None,
    source_files: List[str] = None
) -> List[SearchResult]:
    """Search with metadata pre-filtering."""
    
    def filter_fn(chunk: dict) -> bool:
        meta = chunk.get('metadata', {})
        
        if file_types and meta.get('file_type') not in file_types:
            return False
        
        if source_files and meta.get('filename') not in source_files:
            return False
        
        if date_range:
            created = meta.get('created_at', '')
            if created < date_range[0] or created > date_range[1]:
                return False
        
        return True
    
    return self.vector_store.search(
        self.embedder.embed_query(query),
        k=k,
        filter_fn=filter_fn
    )
```

---

## 9. Evaluation and Iteration

### Retrieval Metrics

```python
from typing import List, Set

def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """What fraction of relevant documents were retrieved in top k?"""
    retrieved_k = set(retrieved[:k])
    return len(retrieved_k & relevant) / len(relevant) if relevant else 0.0

def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
    """What fraction of retrieved documents are relevant?"""
    retrieved_k = set(retrieved[:k])
    return len(retrieved_k & relevant) / k if k > 0 else 0.0

def mrr(retrieved: List[str], relevant: Set[str]) -> float:
    """Mean Reciprocal Rank - where does the first relevant doc appear?"""
    for i, doc_id in enumerate(retrieved):
        if doc_id in relevant:
            return 1.0 / (i + 1)
    return 0.0

def ndcg_at_k(retrieved: List[str], relevance_scores: dict, k: int) -> float:
    """Normalized Discounted Cumulative Gain - accounts for graded relevance."""
    import numpy as np
    
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k]):
        rel = relevance_scores.get(doc_id, 0)
        dcg += rel / np.log2(i + 2)  # +2 because i is 0-indexed
    
    # Ideal DCG
    ideal_rels = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_rels))
    
    return dcg / idcg if idcg > 0 else 0.0
```

### End-to-End Evaluation

```python
class RAGEvaluator:
    def __init__(self, rag_pipeline: RAGPipeline, llm_client):
        self.rag = rag_pipeline
        self.llm = llm_client
    
    def evaluate_faithfulness(self, question: str, answer: str, context: str) -> float:
        """Does the answer only contain information from the context?"""
        prompt = f"""Evaluate if the following answer is faithful to the provided context.
A faithful answer only makes claims that are supported by the context.

Context: {context}

Question: {question}

Answer: {answer}

Rate faithfulness from 0.0 (completely unfaithful) to 1.0 (completely faithful).
Respond with just the number."""
        
        score = float(self.llm.generate(prompt, max_tokens=10).strip())
        return max(0.0, min(1.0, score))
    
    def evaluate_relevance(self, question: str, answer: str) -> float:
        """Does the answer actually address the question?"""
        prompt = f"""Rate how well this answer addresses the question.

Question: {question}

Answer: {answer}

Rate from 0.0 (completely irrelevant) to 1.0 (perfectly addresses the question).
Respond with just the number."""
        
        score = float(self.llm.generate(prompt, max_tokens=10).strip())
        return max(0.0, min(1.0, score))
    
    def evaluate_context_relevance(self, question: str, contexts: List[str]) -> float:
        """Are the retrieved contexts relevant to the question?"""
        scores = []
        for ctx in contexts:
            prompt = f"""Rate the relevance of this context for answering the question.

Question: {question}

Context: {ctx}

Rate from 0.0 (not relevant) to 1.0 (highly relevant).
Respond with just the number."""
            
            score = float(self.llm.generate(prompt, max_tokens=10).strip())
            scores.append(max(0.0, min(1.0, score)))
        
        return sum(scores) / len(scores) if scores else 0.0
```

### Building a Test Suite

```python
# Example evaluation dataset
eval_dataset = [
    {
        "question": "What is the company's refund policy?",
        "relevant_doc_ids": ["policies_doc_3", "policies_doc_4"],
        "expected_answer_contains": ["30 days", "full refund", "original payment"]
    },
    {
        "question": "How do I reset my password?",
        "relevant_doc_ids": ["faq_doc_12"],
        "expected_answer_contains": ["email", "reset link", "24 hours"]
    }
]

def run_evaluation(rag: RAGPipeline, evaluator: RAGEvaluator, dataset: List[dict]):
    results = {
        'recall@5': [],
        'mrr': [],
        'faithfulness': [],
        'relevance': []
    }
    
    for item in dataset:
        # Run retrieval
        query_result = rag.query(item['question'])
        retrieved_ids = [r.chunk_id for r in query_result['retrieved_chunks']]
        
        # Retrieval metrics
        relevant = set(item['relevant_doc_ids'])
        results['recall@5'].append(recall_at_k(retrieved_ids, relevant, 5))
        results['mrr'].append(mrr(retrieved_ids, relevant))
        
        # Generation metrics (requires actual LLM call)
        # answer = llm.generate(query_result['prompt'])
        # results['faithfulness'].append(evaluator.evaluate_faithfulness(...))
    
    # Aggregate
    return {k: sum(v)/len(v) for k, v in results.items() if v}
```

---

## Key Takeaways

1. **Chunking matters most** - Spend time getting chunk boundaries right. Semantic coherence beats arbitrary size limits.

2. **Hybrid search outperforms pure vector** - Combining BM25 keyword matching with embeddings catches cases where one alone fails.

3. **Reranking is cheap insurance** - Cross-encoders add latency but significantly improve precision when retrieval is noisy.

4. **Context position affects attention** - Place most relevant chunks at the start and end; the middle gets less attention ("lost in the middle").

5. **Contextual chunks improve retrieval** - Prepending document/section context to each chunk helps embeddings capture relevance.

6. **Evaluate iteratively** - Build a test set early and measure after each change. Small improvements compound.

7. **Cache aggressively** - Embeddings and common queries benefit enormously from caching.

8. **Metadata enables filtering** - Store rich metadata at indexing time; it's expensive to add later.

This architecture scales from a few documents to millions with appropriate index types (HNSW for medium scale, IVF for larger). Start simple with flat indices and recursive chunking, then optimize based on measured bottlenecks.

</explanation>
