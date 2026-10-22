# Deployment & Operations Guide

## 1. Quick Start via Docker Compose (Recommended)

To run the complete system with PostgreSQL (pgvector), Redis, Celery worker, FastAPI backend, and React frontend:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Build and start services in the background
docker-compose up --build -d

# 3. Verify health
docker-compose ps
curl http://localhost:8000/health/ready
```

Services will be available at:
- **Frontend App**: `http://localhost:3000` (or `http://localhost:5173`)
- **FastAPI API**: `http://localhost:8000`
- **Swagger Documentation**: `http://localhost:8000/api/v1/docs`

---

## 2. Local Development Setup (Manual)

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16 with `pgvector`
- Redis server

### Step 1: Database & Redis

```bash
# Start PostgreSQL & Redis services (e.g. Homebrew on macOS)
brew services start postgresql@16
brew services start redis

# Create database
psql -d postgres -c "CREATE DATABASE codebase_intelligence;"
psql -d codebase_intelligence -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Step 2: Backend Setup

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Start background worker (in separate terminal)
celery -A app.workers.celery_app worker --loglevel=info

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### Step 3: Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to access the application.
