# Codebase Intelligence — AI Codebase Assistant

> On this computer, use **http://127.0.0.1:3002/** for the app and **http://127.0.0.1:8002/api/v1/docs** for the API. See [LOCAL_SETUP.md](LOCAL_SETUP.md) for the configured ports, commands, and mock-answer limitation. These ports let TaskFlow continue running alongside this project.

[![CI Pipeline](https://github.com/developer/codebase-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/developer/codebase-intelligence/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16 + pgvector](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg)](https://github.com/pgvector/pgvector)
[![Vite + React](https://img.shields.io/badge/frontend-React%20%2B%20Vite%20%2B%20Monaco-61dafb.svg)](https://vitejs.dev/)

**Codebase Intelligence** is a production-grade, multi-tenant AI developer assistant that enables software engineers to upload codebases as `.zip` archives and ask natural language questions about their architecture, functions, database connections, and request flows.

The system retrieves relevant source code using **Tree-sitter AST syntax parsing**, **hybrid search (pgvector + PostgreSQL full-text search)**, and **Reciprocal Rank Fusion (RRF)**, producing evidence-grounded answers with verifiable file citations and line numbers that jump directly to source code in an integrated **Monaco Editor**.

---

## Architecture Overview

```
User uploads ZIP
       │
       ▼
Secure ZIP Extraction (Zip slip, symlink, and zip bomb validation)
       │
       ▼
File Discovery & Filtering (.git, node_modules, binaries, secrets ignored)
       │
       ▼
Tree-sitter AST Parsing (Extracts functions, classes, and method boundaries)
       │
       ▼
Syntax-Aware Chunking (Exact start/end lines preserved)
       │
       ▼
Embedding Generation (BAAI/bge-small-en-v1.5)
       │
       ▼
PostgreSQL + pgvector (HNSW vector index + GIN full-text index)
       │
       ▼
Hybrid Search (RRF) + Grounded LLM Generation with Validated Citations
```

---

## Key Features

- **AST-Aware Code Parsing**: Uses Tree-sitter for Python, JavaScript, TypeScript, Java, C, and C++ to extract logical symbol boundaries.
- **Hybrid Retrieval**: Combines pgvector cosine similarity with PostgreSQL full-text search via Reciprocal Rank Fusion ($k=60$).
- **Evidence-Grounded Citations**: LLM responses cite original filenames and line numbers; clicking a citation jumps directly to the line in Monaco Editor.
- **Untrusted Code Security**:
  - Rejects Zip Slip path traversals (`..`), absolute paths, and malicious symlinks.
  - Mitigates zip bomb compression ratio exploits.
  - Two-stage secret protection: automatically excludes `.env` and credentials from indexing, and redacts sensitive patterns before LLM prompt assembly.
  - Uploaded code is **never executed**.
- **Multi-Tenant Data Isolation**: All database queries and vector similarity searches enforce object-level ownership checks.
- **Developer UI**: Dark theme, Monaco code viewer with line highlight decorations, interactive file tree, and chat history.
- **Asynchronous Processing**: Background indexing via Redis and Celery with progress tracking.

---

## RAG Evaluation Benchmark Results

Evaluated against the sample microservice repository across 4 retrieval strategies:

| Retrieval Strategy | Recall@1 | Recall@3 | Recall@5 | MRR | Latency |
|---|---|---|---|---|---|
| **Vector-only (`pgvector`)** | 1.00 | 1.00 | 1.00 | 1.0000 | 26.25ms |
| **Keyword-only (PostgreSQL FTS)** | 0.00 | 0.00 | 0.00 | 0.0000 | 2.40ms |
| **Hybrid Retrieval (RRF)** | **1.00** | **1.00** | **1.00** | **1.0000** | **21.91ms** |
| **Hybrid + Cross-Encoder Reranker** | 0.67 | 1.00 | 1.00 | 0.8333 | 5,193ms (init) |

*Key finding:* Keyword search alone struggles with conceptual natural language queries (*"Explain how database connection works"*), whereas semantic vector embeddings achieve perfect recall. Hybrid RRF combines the best of both worlds with ultra-low latency (~22ms).

---

## Quick Start with Docker Compose

```bash
# 1. Clone repository and copy environment configuration
cp .env.example .env

# 2. Start all containers in the background
docker-compose up --build -d

# 3. Access web application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/api/v1/docs
```

---

## Local Development Setup

### 1. Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 16 with `pgvector`
- Redis server

### 2. Backend Setup
```bash
# 1. Start PostgreSQL and Redis (macOS Homebrew example)
brew services start postgresql@16
brew services start redis

# 2. Create PostgreSQL database and enable vector extension
psql -d postgres -c "CREATE DATABASE codebase_intelligence;"
psql -d codebase_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 3. Setup Python virtual environment
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 4. Run database migrations
alembic upgrade head

# 5. Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

---

## Running the Automated Test Suite

```bash
cd backend
source .venv/bin/activate
pytest -v
```

All 12 test suites cover:
- Zip Slip path traversal mitigation
- Symlink and zip bomb detection
- Secret filtering and LLM redaction
- Tree-sitter AST parsing and exact line number preservation
- End-to-end project upload, status transitions, search, and RAG chat

---

## Documentation Index

- [System Architecture](docs/ARCHITECTURE.md)
- [Database Schema & Indexes](docs/DATABASE.md)
- [RAG Pipeline & Retrieval Strategy](docs/RAG_PIPELINE.md)
- [REST API Reference](docs/API.md)
- [Security Threat Model](docs/SECURITY.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [RAG Learning Guide & Interview Questions](docs/LEARNING.md)
- [Implementation Progress](docs/PROGRESS.md)

---

## License

MIT License. Designed and engineered for high-performance codebase understanding.
