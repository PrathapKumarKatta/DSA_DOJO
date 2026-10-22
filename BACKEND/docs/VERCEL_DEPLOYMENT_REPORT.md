# TaskFlow: Vercel Deployment Readiness Report

Review date: 2026-10-22

## What the project contains

TaskFlow is a React/TypeScript/Vite client and a FastAPI service. The API relies on PostgreSQL and Redis. Celery worker and beat processes handle task reminders. The repository also includes a Docker Compose stack suitable for local development and a separate single-VM deployment example.

## Vercel deployment boundary

The frontend is configured for Vercel as a Vite single-page app. Vercel builds `frontend` with `npm run build`, publishes `dist`, and routes client-side paths back to `index.html`. Set the Vercel project Root Directory to `BACKEND/frontend` when importing the DSA_DOJO repository.

Vercel deployment of this frontend does not host the complete TaskFlow service. Deploy the FastAPI API, PostgreSQL, Redis, one Celery worker, and one Celery beat process on an always-running container or app platform first. The provided `docs/deployment` example documents one Linux VM topology. Add the deployed API origin to the Vercel project's `VITE_API_BASE_URL` environment variable, with no trailing slash, and set the API's `CORS_ORIGINS` to the exact Vercel production origin and any intended preview origins. Rebuild after setting the variable.

## Vercel project settings

- Root Directory: `BACKEND/frontend`
- Framework: Vite
- Install Command: `npm install` (or `npm ci` when a package lock is committed)
- Build Command: `npm run build`
- Output Directory: `dist`
- Environment: `VITE_API_BASE_URL=https://YOUR_TASKFLOW_API_HOST`

The browser calls `/api/v1` and `/health/ready` on that API origin. The API docs link points to `/docs` on the same origin. Local Vite development keeps using its proxy when the environment variable is empty.

## Release checklist

1. Deploy the API, PostgreSQL, Redis, worker, and beat using the deployment guide. Configure real secrets and TLS; do not reuse local `.env` values.
2. Set production `CORS_ORIGINS` to the exact frontend origin. Do not use `*` with credentials.
3. Create the Vercel project with the settings above and set `VITE_API_BASE_URL` for Production and Preview environments as appropriate.
4. Deploy and verify registration, login, workspace creation, task updates, comments, activity, and the `/health/ready` indicator in a browser.
5. Verify that the worker and beat are running and that a due-task reminder is processed. Verify database backups and restore separately.

## Current status and limits

The TaskFlow frontend is deployed at [https://taskflow-app-tau-six.vercel.app](https://taskflow-app-tau-six.vercel.app) and returns HTTP 200. Its Vercel project is `taskflow-app`, with root directory `BACKEND/frontend`, Vite build settings, and public access enabled. The build currently has no `VITE_API_BASE_URL`, so login and all API-backed features need a separately hosted TaskFlow API. Set that URL in Vercel and configure production `CORS_ORIGINS` before using the app. The API's console email adapter does not send real email.

Vercel Git auto-deployment is not connected. The CLI connection attempt was rejected because the Git integration is not available to this project; connect the DSA_DOJO repository from Vercel's project settings to enable deployments on future pushes. The deployment was published from the pushed `codex/vercel-deployment-reports` branch.
