# Codebase Intelligence: Vercel Deployment Readiness Report

Review date: 2026-10-22

## What the project contains

The project has a React/TypeScript/Vite frontend and a FastAPI backend. Backend services include PostgreSQL with pgvector, Redis, Celery ingestion workers, local extracted-file storage, sentence-transformer embeddings, and a configurable LLM provider. Docker Compose runs the full local stack.

## Vercel deployment boundary

The frontend is configured for Vercel as a Vite single-page app. Set the Vercel project's Root Directory to `RAG/codebase-intelligence/frontend` when importing the DSA_DOJO repository, or to `frontend` when importing the Codebase Intelligence repository directly. Vercel builds with `npm run build`, publishes `dist`, and routes client-side paths back to `index.html`.

The frontend deployment alone does not provide the API, database, ingestion worker, Redis, or persistent uploaded-file storage. The backend uses long-lived Celery work and writes extracted project files to its storage directory. Deploy those components on a container platform with persistent storage and a PostgreSQL service that supports pgvector. Set `VITE_API_BASE_URL` to the backend origin and set `BACKEND_CORS_ORIGINS` on the backend to the exact Vercel production origin and any intended preview origins. Keep LLM keys in backend secrets, never in Vite variables.

The repository's mock LLM provider is suitable for a local/demo response only. Select and configure a real provider on the backend before presenting generated answers as model output. Embeddings currently run with sentence-transformers; hosting that model in a serverless API may exceed package/deployment or cold-start budgets, so keep ingestion and embeddings with the worker service.

## Vercel project settings

- Root Directory: `RAG/codebase-intelligence/frontend` (monorepo import) or `frontend` (standalone import)
- Framework: Vite
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment: `VITE_API_BASE_URL=https://YOUR_CODEBASE_API_HOST`

The browser sends `/api/v1` requests to that API origin. Local Vite development keeps using its proxy when the environment variable is empty.

## Release checklist

1. Deploy the API, pgvector database, Redis, Celery worker, and persistent backend storage. Configure real backend secrets.
2. Set `BACKEND_CORS_ORIGINS` to the exact frontend origin; do not expose credentials or provider keys through `VITE_*` variables.
3. Configure the Vercel project and API origin for Production and Preview environments as appropriate.
4. Deploy and verify sign-up, project creation, ZIP upload, ingestion completion, search, and chat citations against the public services.
5. Confirm worker restart behavior, storage persistence, database backups, upload limits, and provider usage/cost controls.

## Current status and limits

The Codebase Intelligence frontend is deployed at [https://codebase-intelligence-xi.vercel.app](https://codebase-intelligence-xi.vercel.app) and returns HTTP 200. Its Vercel project is `codebase-intelligence`, with root directory `RAG/codebase-intelligence/frontend`, Vite build settings, and public access enabled. The build currently has no `VITE_API_BASE_URL`, so sign-in, uploads, search, and chat need a separately hosted backend. Set that URL in Vercel and add the production frontend origin to `BACKEND_CORS_ORIGINS` before using the app. The backend also needs PostgreSQL with pgvector, Redis, a Celery worker, and persistent uploaded-file storage. The currently configured mock LLM provider does not produce real model answers.

Vercel Git auto-deployment is not connected. The CLI connection attempt was rejected because the Git integration is not available to this project; connect the DSA_DOJO repository from Vercel's project settings to enable deployments on future pushes. The deployment was published from the pushed `codex/vercel-deployment-reports` branch.
