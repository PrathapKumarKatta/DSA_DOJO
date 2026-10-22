# Local setup on this computer

This checkout is in `DSA_DOJO/RAG/codebase-intelligence`. Local configuration uses separate ports so the TaskFlow project in BACKEND can continue running.

| Service | Address |
| --- | --- |
| Application | http://127.0.0.1:3002/ |
| API documentation | http://127.0.0.1:8002/api/v1/docs |
| Readiness | http://127.0.0.1:8002/health/ready |
| PostgreSQL | 127.0.0.1:5433 |
| Redis | 127.0.0.1:6380 |

Run these commands in PowerShell from this checkout:

```powershell
docker compose up -d --build
docker compose ps
docker compose logs --tail 80 backend worker
```

Open the application, register an account, create a project, upload a source-code ZIP, and wait for its status to become ready. Then open the explorer or ask a question in chat. A sample ZIP is generated at `sample_projects/microservice.zip` by the local smoke script.

The backend and worker use real `BAAI/bge-small-en-v1.5` embeddings on CPU. The first indexing operation downloads the model; its cache persists in a Docker volume. The first search in the API process must also load the model into memory.

**Answer generation defaults to `LLM_PROVIDER=mock`.** It returns a template based on retrieved source citations, rather than a real language-model explanation. No paid provider was configured. To use a provider later, configure the LLM environment values and recreate the backend; the provider implementations are in `backend/app/rag/llm_adapter.py`. Do not commit API keys.

Local changes repair the Docker package build, use CPU PyTorch, keep bcrypt compatible with the existing Passlib integration, initialize pgvector before schema creation, run migrations before API startup, and wait for backend health before starting the worker. Generated database/JWT secrets live in ignored `.env`. Docker volumes persist the database, uploaded sources, and downloaded models.

The worker explicitly imports `app.workers.tasks` on startup. The original worker command did not register the ingestion task and discarded upload jobs; the local Compose command fixes that registration.

## Verified local result

On 22 October 2026, the local smoke run passed registration/login, ZIP upload through the frontend proxy, Celery indexing with real BGE embeddings, retrieval, and mock-answer chat citations. The sample microservice produced **6 indexed files and 24 chunks**, with 5 retrieval results and 3 chat citations for the database-connection question. The app's sign-in page was also opened in the in-app browser. This was a local smoke check, not a complete browser regression suite or a public deployment.

To inspect the pre-indexed sample project, sign in with the generated credentials in `.local-demo.json` beside this guide. Alternatively, register your own account and upload `sample_projects/microservice.zip`.

The optional `scripts/local_smoke.py` exercises readiness, registration, login, sample upload, background indexing, retrieval, and chat through the frontend proxy. It uses Python with httpx installed, creates one local demo project, and stores generated sign-in credentials in ignored `.local-demo.json`. It leaves the sample project available for inspection. Credentials and access tokens are not printed.

With uv installed, run it from this checkout using:

```powershell
uv run --link-mode copy --with httpx python scripts/local_smoke.py
```

Stop this project while retaining its data:

```powershell
docker compose down
```

Use `docker compose up -d` to start it again. Do not add `--volumes` when stopping if you want to retain your local data. These are local development settings, not a public deployment.
