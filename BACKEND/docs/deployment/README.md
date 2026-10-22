# TaskFlow public deployment learning example

These files document a **single Linux VM portfolio deployment**, with PostgreSQL and Redis on the same host and HTTPS through Caddy. They are a standalone deployment configuration, not a local Compose override. They have not been deployed to a public server. Compose syntax and mounted nginx configuration can be checked locally; public DNS, certificate issuance, SMTP and restore operations still need validation in your environment.

Read chapters 17–19 of the handbook before using this example. A single host is a failure domain. For a business service, assess managed PostgreSQL, off-host backups, availability, email verification, abuse protection and operational ownership first. No hosting account, domain or paid resource is created by this documentation task.

This learning example uses the database bootstrap account as the app account. Before business use, introduce a separate migration role and a runtime role with only necessary privileges. The public registration and demo flows also need their own abuse/resource controls; the existing limiter covers login only.

## Prerequisites

- An Ubuntu 24.04 LTS server, an SSH key, and a non-root administrative login.
- Docker Engine and the Compose plugin installed from [Docker's official Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
- A real domain or subdomain with its A record pointing at this server. Publish an AAAA record only if IPv6 actually reaches the server.
- Provider firewall rules allowing public TCP 80/443 and SSH only from your administrative IP. These files expose no database, Redis or application port directly.
- Access to clone your repository onto the server, without committing authentication tokens.
- A non-overlapping Docker subnet. The example uses 172.30.50.0/24 and trusts only the frontend address 172.30.50.10 at the API. If changing the subnet, update both places.

## Required application adjustment before a public release

`frontend/src/App.tsx` currently links the API docs to `http://127.0.0.1:8000/docs`. For a public build, change that link to `/docs`. This nginx example proxies `/docs`, `/redoc`, and `/openapi.json` to the API. To keep the relative link working during Vite development, add matching `/docs` and `/openapi.json` proxy entries to `frontend/vite.config.ts`, using the existing API target. Rebuild the frontend after that change. This documentation does not silently modify application code.

## Initial release on the server

Connect from Windows PowerShell with `ssh YOUR_ADMIN_USER@YOUR_SERVER_IP`, replacing both placeholders with the account and address from your provider. Verify the server identity through your provider's information when connecting for the first time.

The following commands are **Bash on the Linux server**. Replace `YOUR_REPOSITORY_URL` with the clone URL from your GitHub repository, and use your normal Git authentication flow without embedding a token in the command:

```bash
git clone YOUR_REPOSITORY_URL taskflow-source
cd taskflow-source/BACKEND
```

From that `BACKEND` folder, run:

```bash
cp docs/deployment/.env.production.example .env.production
chmod 600 .env.production
```

Generate three different URL-safe strings, for example with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'` three times. Edit `.env.production` with the real domain, contact email and three generated secrets. The sample domain and email are not working deployment values. Keep the root `.env.production` untracked; the existing `.gitignore` is extended for that file.

Define a short Bash helper in this shell:

```bash
dc() {
  docker compose --env-file .env.production \
    -f docs/deployment/compose.production.yaml "$@"
}
```

If your Docker installation requires sudo, use sudo before docker in the helper. Membership in the Docker group grants substantial host privileges; follow the official installation guide's security guidance rather than broadening access casually.

```bash
dc config --quiet
dc build api worker beat migrate frontend
dc up -d db redis
dc run --rm migrate
dc up -d api worker beat
dc up -d frontend proxy
dc ps
```

Stop and fix any failed command before running the next. Migrations run once as an explicit release job. Do not scale beat beyond one instance. Caddy should obtain a certificate after DNS resolves and public ports are reachable. Verify with your real domain:

```bash
curl --fail https://YOUR_DOMAIN/health/ready
curl --fail --output /dev/null https://YOUR_DOMAIN/
```

Then use a separate device to register, sign in, create a workspace/project/task, save an update, and read it after refresh. Test isolation with a second account. Do not use `curl -k` to turn a certificate failure into a passing check.

## Client addresses and login throttling

The only public entry point is Caddy. It sets forwarded client headers, nginx preserves those headers, and Uvicorn trusts forwarded headers only from nginx's fixed private address. This example assumes there is no CDN or additional proxy in front of Caddy. If adding one, review trusted proxy configuration at every hop; do not blindly trust all forwarded headers.

This matters because login throttling uses the request's client IP. The original local stack intentionally ignores forwarded headers and therefore sees the local proxy as a shared client.

## Releases and rollback

Use new version tags for APP_IMAGE and WEB_IMAGE on each release, and retain the prior images. Back up before a migration. Pull the intended Git revision, rebuild, run the migration job, update API/worker/beat, then recreate frontend and proxy after API health succeeds:

```bash
dc build api worker beat migrate frontend
dc run --rm migrate
dc up -d api worker beat
dc up -d --force-recreate frontend proxy
dc ps
```

Recreating nginx refreshes its resolution of the API service if Docker changed that container's address. This simple release may have brief downtime. Do not call it a zero-downtime deployment.

For an application rollback, set the previous image tags in `.env.production` and use `dc up -d --no-build api worker beat`, followed by `dc up -d --no-build --force-recreate frontend proxy`. This works only if the database schema remains compatible with the old application. Never automatically run Alembic downgrade against production as a generic rollback.

## Backups and a restore exercise

The following is Bash binary redirection on the Linux server, not older Windows PowerShell redirection. Choose an explicit backup name and retain access restrictions:

```bash
mkdir -p backups
chmod 700 backups
dc exec -T db pg_dump -U taskflow -d taskflow -Fc > backups/taskflow-before-release.dump
chmod 600 backups/taskflow-before-release.dump
```

Copy backups to protected off-host storage under your own access controls. An on-server backup can be lost with that server. Test restoration into a **separate empty database**:

```bash
dc exec -T db createdb -U taskflow taskflow_restorecheck
dc exec -T db pg_restore -U taskflow -d taskflow_restorecheck \
  --exit-on-error < backups/taskflow-before-release.dump
dc exec -T db psql -U taskflow -d taskflow_restorecheck \
  -c 'SELECT count(*) FROM tasks;'
```

If that restore database already exists, choose a new isolated name; do not overwrite a database merely to make the example run. Check expected tables, counts and sample relationships before treating the restore as verified. Decide a retention schedule and recovery objectives, and measure them.

## What remains to verify publicly

HTTPS, actual DNS and firewall behavior; client IP throttling through the real proxy chain; cold restart; off-host backup and isolated restore; real SMTP delivery if enabled; capacity under representative load; alerts and recovery ownership. Keep credentials out of screenshots, commit history and public command output.

References: [Compose in production](https://docs.docker.com/compose/how-tos/production/), [Compose networking](https://docs.docker.com/compose/how-tos/networking/), [Caddy proxy headers](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
