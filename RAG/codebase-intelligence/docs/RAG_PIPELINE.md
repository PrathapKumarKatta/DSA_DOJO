# RAG Pipeline & Retrieval Strategy

This document details the design, algorithms, and evaluation of the Retrieval-Augmented Generation (RAG) pipeline for Codebase Intelligence.

---

## 1. Syntax-Aware Parsing vs. Naive Chunking

Standard document RAG uses fixed character windows (e.g. 500 characters with 50-character overlap). While suitable for prose, naive chunking breaks code logic:
- Functions are severed midway through variable definitions or loops.
- Indentation and scope boundaries are destroyed.
- Symbol relationships (which function belongs to which class) are lost.

### Tree-sitter Abstract Syntax Tree (AST) Parsing

Codebase Intelligence utilizes **Tree-sitter** grammar parsers for Python, JavaScript, TypeScript, Java, C, and C++.

```
   Source Code File
          │
          ▼
   Tree-sitter Parser
          │
          ├─ module node ───▶ Module Chunk (Imports, Docstrings, Constants)
          │
          ├─ class_definition ───▶ Class Header & Methods
          │
          └─ function_definition ──▶ Function Chunk
                                    - Exact start_line & end_line
                                    - Preserved identifier name
```

If a single function or class exceeds `MAX_CHUNK_LINES = 80`, it is divided using sliding windows with a 15-line overlap while preserving original line numbers.

---

## 2. Hybrid Retrieval with Reciprocal Rank Fusion (RRF)

Semantic vector similarity and lexical keyword search exhibit complementary strengths:
- **Vector Search (pgvector)**: Excellent at conceptual queries (e.g., *"How is database connection pooling handled?"* matches `DatabaseManager.connect` even when the word "pooling" is not explicitly mentioned).
- **Keyword Search (PostgreSQL FTS)**: Excellent at exact identifiers, function names, error codes, and configuration keys (e.g., `handle_webhook` or `PAYMENT_GATEWAY_URL`).

### Fusion Formula

Results from both search methods are fused using standard Reciprocal Rank Fusion:

$$RRF(d) = \frac{1}{60 + \text{rank}_{\text{vector}}(d)} + \frac{1}{60 + \text{rank}_{\text{keyword}}(d)}$$

Where:
- $\text{rank}_{\text{vector}}(d)$ is the 1-based rank from pgvector cosine distance.
- $\text{rank}_{\text{keyword}}(d)$ is the 1-based rank from PostgreSQL `ts_rank_cd`.
- The constant $k = 60$ dampens the impact of extreme outliers.

---

## 3. Cross-Encoder Reranking

An optional cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) is available to rerank candidate chunks.

### Trade-Offs

| Metric | Hybrid RRF | Hybrid + Cross-Encoder |
|---|---|---|
| **Recall@3** | 100% | 100% |
| **Recall@5** | 100% | 100% |
| **MRR** | 1.0000 | 0.8333 |
| **Latency** | **21.91ms** | 5,193ms (first load) / ~120ms (cached) |

*Finding:* For targeted codebase search, high-quality BGE-small embeddings combined with AST chunk boundaries achieve top recall without the 100ms+ computational overhead of cross-encoders. Reranking can be enabled via `RERANKING_ENABLED=true` when querying ambiguous natural language prompts.

---

## 4. Citation Validation & Anti-Hallucination

1. **System Prompt Constraint**: The LLM is instructed to answer solely based on the code provided within `<source_code_context>` delimiters.
2. **Deterministic Citation Extraction**: Regex extracts `[File: <path> | Lines: <start>–<end>]` from the response.
3. **Grounding Verification**: Each extracted citation is cross-referenced with the database `code_chunks` retrieved for the project. If a model attempts to invent a file or line range, it is rejected and replaced with the authoritative retrieved chunk references.
