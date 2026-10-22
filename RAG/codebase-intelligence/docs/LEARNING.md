# Learning Guide & Technical Mentorship

This guide breaks down core engineering concepts used in this project for developers and students learning RAG and backend architecture.

---

## 1. Key Concepts Explained

### 1. What is an Embedding?
An embedding converts unstructured text or code into a dense array of floating-point numbers (a high-dimensional vector, e.g. 384 dimensions for `BAAI/bge-small-en-v1.5`). 
Texts with similar semantic meaning end up close together in geometric vector space, allowing cosine similarity to find conceptual matches even when keywords differ.

### 2. Why Tree-sitter AST Parsing?
Traditional RAG splits text by characters or sentences. But code has strict grammar and scope. If you cut a Python function in half, the model sees orphaned variables without context. Tree-sitter generates an Abstract Syntax Tree (AST), allowing us to locate exact function, class, and method boundaries with 100% accurate start and end line numbers.

### 3. Bi-Encoder vs. Cross-Encoder
- **Bi-Encoder (Embedding Model)**: Encodes query and document separately into vectors. Similarity is calculated with vector dot product or cosine distance. This is ultra-fast ($< 25\text{ms}$) and can scale to millions of chunks via pgvector HNSW indexes.
- **Cross-Encoder (Reranker)**: Feeds query and document together into the transformer attention mechanism simultaneously. This captures deeper cross-attention interactions but is computationally heavy ($> 100\text{ms}$ per batch). We use it only to rerank the top candidates.

### 4. Reciprocal Rank Fusion (RRF)
When combining vector similarity and keyword search, standard scores cannot be added directly because cosine similarity ($0.0 \dots 1.0$) and BM25/ts_rank ($0.0 \dots \infty$) are on completely different scales.
RRF bypasses score calibration by using **rank positions**:
$$RRF(d) = \sum_{m} \frac{1}{60 + \text{rank}_m(d)}$$
This provides robust, unbiased hybrid retrieval.

---

## 2. Common Technical Interview Questions

### Q1: Why not just send the whole repository to an LLM with a 1M token context window?
1. **Cost**: Sending 500,000 tokens per developer question becomes prohibitively expensive.
2. **Latency**: Massive context windows take 15–30 seconds for initial prompt pre-filling.
3. **Lost in the Middle**: LLMs degrade in accuracy when critical evidence is buried inside thousands of lines of irrelevant boilerplate.
4. **Security**: Full repo dumps increase exposure of sensitive logic or accidental secrets.

### Q2: How do you prevent multi-tenant data leakage in vector databases?
Never execute unscoped vector searches. Always apply metadata filtering before or during vector distance computation:
```sql
SELECT * FROM code_chunks
WHERE project_id = :project_id
ORDER BY embedding <=> :query_vector
LIMIT :top_k;
```
Combined with object-level checks ensuring the authenticated user owns `:project_id`.

### Q3: How do you ensure the LLM cites accurate line numbers?
Do not ask the LLM to guess line numbers. During ingestion, the Tree-sitter parser records the exact `start_line` and `end_line` of every chunk. These line numbers are embedded in the prompt header (`[File: auth.py | Lines: 12-45]`). When the LLM references the file, the backend validates the cited line numbers directly against the database chunk table before storing or returning them.
