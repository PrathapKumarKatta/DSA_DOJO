# TaskFlow on Vercel with free data services

TaskFlow can run its React frontend and FastAPI API in one Vercel project using Vercel Services. The API and frontend share the existing TaskFlow Vercel domain. Neon supplies PostgreSQL and Upstash supplies Redis. This is a portfolio/demo setup; free quotas and Vercel function limits apply. The Python service supports FastAPI on Vercel, and Vercel Services are currently in beta on all plans.

## One-time setup

1. Create a Neon Postgres database and copy the connection URI. Preserve `sslmode=require`; the backend converts standard `postgresql://` URLs to the asyncpg URL it needs.
2. Create an Upstash Redis database and copy its `rediss://` Redis protocol URL. Do not use the REST URL/token pair.
3. In the `taskflow-app` Vercel project, change **Root Directory** to `BACKEND` and redeploy the `codex/vercel-deployment-reports` branch. The repository-root-in-project `BACKEND/vercel.json` routes `/api/*`, `/health*`, `/docs*`, `/redoc*`, and `/openapi.json` to FastAPI; other paths go to the Vite frontend.
4. Add these Production environment variables to the Vercel project:
   - `DATABASE_URL`: Neon connection URI
   - `REDIS_URL`: Upstash Redis protocol URI
   - `JWT_SECRET`: a newly generated secret with at least 32 characters
   - `ENVIRONMENT`: `production`
   - `CORS_ORIGINS`: JSON list containing `https://taskflow-app-tau-six.vercel.app`
5. Redeploy. The production build runs Alembic migrations against Neon before publication. The frontend leaves `VITE_API_BASE_URL` empty so API calls use the same Vercel domain.

## Verify

- `https://taskflow-app-tau-six.vercel.app/health/ready` must return JSON `{"status":"ready"}`.
- `https://taskflow-app-tau-six.vercel.app/docs` must show TaskFlow's API docs.
- Register, sign in, create a workspace and task, refresh, and confirm the task remains.

Vercel Functions can sleep between requests or encounter free-plan quota limits. Upstash and Neon free quotas apply. The deployment does not run the Celery worker or beat process, so scheduled reminder emails are unavailable in this free setup. Do not send database URLs or JWT secrets in chat or commit them to Git.
