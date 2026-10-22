# TaskFlow free demo deployment

This setup keeps the Vercel frontend and deploys the FastAPI API as a Render free web service. It uses Neon free Postgres and Upstash free Redis. The Blueprint intentionally creates only the API service; it never provisions paid services or databases.

## Free-tier limits

- The Render API sleeps after inactivity, so the first request can take a while to wake it.
- Neon and Upstash free quotas apply. Keep this to a portfolio/demo workload.
- Task creation, projects, workspaces, login, and database-backed features work. Due-date reminder emails are not processed because the free setup does not run the Celery worker/beat; email delivery is also set to the console adapter.
- This is not a production availability or backup setup.

## Deploy the API

1. Create a Neon Postgres project and copy its connection URI. Keep `postgresql://` as provided; the API converts it to its required async SQLAlchemy driver. Preserve `sslmode=require` in the URI.
2. Create an Upstash Redis database with the Redis protocol and copy its `rediss://` connection URI (not the REST URL or token).
3. In Render, create a Blueprint from the `codex/vercel-deployment-reports` branch of `PrathapKumarKatta/DSA_DOJO`. Select the repository-root `render.yaml`.
4. When Render prompts for `DATABASE_URL` and `REDIS_URL`, paste the Neon and Upstash connection URIs. The Blueprint generates `JWT_SECRET` and sets the production CORS origin to the TaskFlow Vercel site.
5. Deploy the Blueprint. Wait for the service health check to pass, then verify `https://<render-service>.onrender.com/health/ready` returns `{"status":"ready"}`.

## Connect the Vercel frontend

In the `taskflow-app` Vercel project's Production environment, set `VITE_API_BASE_URL` to the Render service origin, for example `https://taskflow-api-abcd.onrender.com` (no trailing slash). Redeploy the frontend so the URL is included in the Vite build.

Then verify registration, login, workspace and task creation, and refresh persistence. The first API request after the Render service sleeps may be delayed.
