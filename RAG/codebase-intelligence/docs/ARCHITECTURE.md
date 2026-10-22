# System Architecture — Codebase Intelligence

## 1. High-Level Overview

Codebase Intelligence is an AI-powered code search and architecture analysis platform designed specifically for engineering teams to understand complex, unfamiliar, or legacy repositories without uploading code to third-party code hosting integrations.

Developers upload repositories as `.zip` archives. The system extracts files securely, inspects syntax using Tree-sitter Abstract Syntax Trees (AST), generates semantic and lexical search representations in PostgreSQL with `pgvector`, and provides an evidence-grounded conversational interface with source citations.

```
                          ┌─────────────────────────────────────┐
                          │         React Frontend (Vite)       │
                          │ Monaco Editor, TanStack Query, Chat │
                          └──────────────────┬──────────────────┘
                                             │ HTTP / REST
                                             ▼
                          ┌─────────────────────────────────────┐
                          │          FastAPI Backend            │
                          │  Auth, Tenancy, Search, Chat, Jobs  │
                          └───────┬───────────────────┬─────────┘
                                  │                   │
                     Enqueue Job  │                   │ Queries / Vectors
                                  ▼                   ▼
     ┌───────────────────────────────────┐    ┌───────────────────────────────────┐
     │       Redis / Celery Worker       │    │       PostgreSQL 16 + pgvector    │
     │  ZIP Extractor, AST Symbol Parser │───▶│   Users, Projects, SourceFiles,   │
     │  BGE-small Embedding Generator    │    │   CodeChunks, Chats, Citations    │
     └───────────────────────────────────┘    └───────────────────────────────────┘
```

---

## 2. Component Design & Clean Architecture

The backend follows the principles of Clean Architecture and Domain-Driven Design (DDD):

1. **API Layer (`app/api/`)**:
   - Thin REST controllers responsible for HTTP input validation, status codes, and routing.
   - Decoupled from direct database queries via Dependency Injection (`app/api/deps.py`).

2. **Service Layer (`app/services/`)**:
   - Encapsulates business logic, transactional operations, and multi-tenant authorization guards.
   - `AuthService`, `ProjectService`, `IngestionService`, `RetrievalService`, `ChatService`.

3. **Repository Layer (`app/repositories/`)**:
   - Isolates SQLAlchemy data queries and entity hydration from business rules.
   - `UserRepository`, `ProjectRepository`, `FileRepository`, `ChunkRepository`, `JobRepository`, `ChatRepository`.

4. **RAG Domain Core (`app/rag/`)**:
   - `file_discovery.py`: Zip Slip defense, symlink rejection, bomb mitigation, extension filters.
   - `secret_filter.py`: Regex pattern detection for API keys, tokens, and private keys.
   - `parser.py`: Tree-sitter AST symbol extractor (Python, JS, TS, Java, C, C++) with indentation fallback.
   - `chunker.py`: Syntax-aware chunking preserving exact line numbers and symbol names.
   - `embeddings.py`: SentenceTransformers embedding provider with batching and local caching.
   - `vector_store.py`: Cosine similarity via `pgvector` and PostgreSQL Full-Text Search.
   - `hybrid_search.py`: Reciprocal Rank Fusion (RRF with $k=60$).
   - `reranker.py`: Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) reranking.
   - `llm_adapter.py`: Provider-agnostic LLM interface supporting local mock, Groq, OpenAI, and Ollama.
   - `citations.py`: Strict validation of model citations against project chunks.

5. **Data Layer (`app/models/`, `app/db/`)**:
   - Declarative SQLAlchemy models with UUID primary keys and cascading foreign keys.
   - Vector columns (`Vector(384)`) with HNSW index and TSVECTOR columns with GIN index.

---

## 3. Data Flow Pipelines

### Pipeline A — Ingestion

1. Developer uploads `.zip` via `POST /api/v1/projects/{id}/upload`.
2. Controller verifies project ownership and file limits (< 50MB).
3. `IngestionJob` record created with status `pending`.
4. Job dispatched to background worker (Celery task with Redis broker, falling back to background worker).
5. Zip entries scanned for zip slip (`..`), absolute paths, symlinks, and compression ratios.
6. Allowed files extracted; ignored directories (`.git`, `node_modules`, `venv`, binaries) excluded.
7. Discovered files parsed using Tree-sitter AST to identify functions, classes, and methods.
8. Chunks generated with exact `start_line` and `end_line` coordinates.
9. Chunks embedded in batches using `BAAI/bge-small-en-v1.5`.
10. Vectors and tsvectors stored in PostgreSQL. Project marked `ready`.

### Pipeline B — Question Answering (RAG)

1. Developer asks a question in `POST /api/v1/projects/{id}/chat`.
2. Query vector generated using embedding provider.
3. Vector similarity search executes against project's chunks (`<=>` cosine distance).
4. Full-text keyword search executes against `search_vector` (`plainto_tsquery`).
5. Reciprocal Rank Fusion merges candidate lists.
6. Optional cross-encoder reranker scores the top candidates.
7. Code context sanitized via secret filter and wrapped in `<source_code_context>` delimiters.
8. LLM receives grounded system prompt enforcing citations and forbidding hallucination.
9. Citations extracted and verified against actual project chunks.
10. Message and citations saved to PostgreSQL; response returned to developer.
