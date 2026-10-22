# Understand TaskFlow with Archify

This is a guided tour of the TaskFlow project you already have. Start with a picture, follow one request into the source, then change and verify one small behavior. You do not need to understand every framework before starting.

Open **index.html** in this folder for the browser reading experience. It links to four real Archify diagrams. Each diagram is a standalone HTML file: it can be viewed without starting TaskFlow, installing Archify globally, or connecting to a database.

The learning reader is also served at [http://127.0.0.1:8011/](http://127.0.0.1:8011/) for this session. To restart that reader later, run the following from BACKEND, leave the terminal running, and open the same address. Stop it with Ctrl+C. This serves only the learning folder on your own computer.

```powershell
uv run python -m http.server 8011 --bind 127.0.0.1 --directory archify-learning
```

## 1. What was downloaded and what was created

There are two separate folders inside BACKEND:

```text
BACKEND/
  archify/                       Downloaded upstream Git repository
    README.md                    Upstream introduction
    LICENSE                      Upstream MIT license
    archify/                     Actual diagram skill package
      SKILL.md                   Instructions for the coding agent
      bin/archify.mjs            Node command line entry point
      schemas/                  Allowed JSON structures
      renderers/                JSON to diagram rendering
      references/               Authoring and delivery rules
    examples/                   Ready-made examples
    viewer/                     Viewer development sources
    test/                       Upstream verification suites
  archify-learning/             Your beginner learning material
    index.html                  Start here in a browser
    README.md                   This editable guide
    sources/                    Four editable JSON diagrams
    diagrams/                   Four HTML diagrams and check receipts
    source-manifest.json        TaskFlow file hashes for this explanation
    build_sources.py            Recreates the initial diagram sources
    build_reader.py             Builds the HTML reader from this guide
    rebuild.ps1                 Renders edited diagram JSON again
```

The upstream download is a shallow clone of [tt-a1i/archify](https://github.com/tt-a1i/archify), pinned initially to **25cf37080fc8b1dbe758a4efc3935b55f3327083**. Its license and original files are preserved. The diagrams and this guide are local additions in the sibling learning folder. The repository was downloaded for local use; no global skill installation was performed.

The doubled path archify/archify is intentional: the outer folder is the downloaded repository; the inner folder contains the skill CLI. Run the commands below from BACKEND unless a different directory is explicitly named.

## 2. Your first tour

Follow this order. Spend time tracing one arrow before opening another map.

| Order | Interactive map | Question it answers |
| --- | --- | --- |
| 1 | [TaskFlow architecture](diagrams/01-taskflow-map.html) | Which component receives my request and where is data saved? |
| 2 | [One task edit](diagrams/02-task-edit.html) | What happens between clicking Save and getting a response? |
| 3 | [Reminder processing](diagrams/03-reminders.html) | Who runs work after the browser request has finished? |
| 4 | [How Archify works](diagrams/04-how-archify-works.html) | How were these interactive diagrams produced? |

In a diagram, select a component to explore its details. Read the cards below the drawing for conditions and limitations. The sequence diagram reads from top to bottom; the vertical distance is **order, not measured time**. The architecture map groups cooperating code into components; it does not claim each box is a separate deployed service.

The first three maps summarize the inspected **local TaskFlow working tree**. Those application files are not committed at the current repository HEAD, so these maps deliberately do not pretend to have commit-verified TaskFlow source badges. The companion file references below and source-manifest.json identify the actual files used. Map 4 has commit-verified source cards for the downloaded Archify repository.

## 3. Learn the minimum vocabulary

| Term | Meaning in this project |
| --- | --- |
| Frontend | React code running in the browser and showing forms, boards, and feedback |
| Backend | FastAPI code that enforces the rules and coordinates storage |
| API | HTTP contract between frontend and backend: URL, method, JSON, and response |
| Route | Python function selected by an HTTP method and path |
| Schema | Pydantic definition of allowed request or response fields |
| Model | SQLAlchemy representation of a database table |
| Service | Code implementing a business action such as updating a task |
| Transaction | Changes that commit together or roll back together |
| Migration | Versioned change to the database structure |
| Authentication | Determining which user is making the request |
| Authorization | Deciding whether that user may perform the action |
| Queue | Messages waiting for a worker to execute work |
| Container | An isolated running process environment packaged from an image |
| Reverse proxy | A server forwarding an incoming request to another service |
| JSON IR | Archify's structured, editable intermediate representation of a diagram |

Use an office analogy: React is the reception desk, FastAPI is the employee checking a request, PostgreSQL is the official records system, Redis holds work messages, Celery workers perform scheduled work, and beat is the timetable. The analogy explains responsibilities; the actual permissions still live in code.

## 4. Run the application and connect it to map 1

Docker Desktop must be running. The existing project setup instructions are in [the backend README](../README.md). If your .env is missing, follow that README to generate the JWT secret first. Never paste a real secret into a diagram.

In Windows PowerShell, from BACKEND:

```powershell
docker compose up -d --build
docker compose ps
```

Open [TaskFlow](http://127.0.0.1:3000/) and [the API documentation](http://127.0.0.1:8000/docs). The Compose migrate service runs Alembic before the application services start. A completed migrate process is normal; it is a one-shot job.

Your browser downloads HTML, CSS, and JavaScript from nginx. React then runs on your computer inside the browser. Requests to /api/v1 go back to nginx, which forwards them to FastAPI. FastAPI uses SQLAlchemy and asyncpg to communicate with PostgreSQL. Read results become JSON and return through nginx to the browser.

Open these files beside map 1:

| File in BACKEND | Look for | What it proves |
| --- | --- | --- |
| [compose.yaml](../compose.yaml) | frontend, api, db, redis, worker, beat, migrate | The actual local processes and their startup dependencies |
| [frontend/nginx.conf](../frontend/nginx.conf) | location /api/ and proxy_pass | nginx forwards API calls; React does not connect to PostgreSQL |
| [frontend/src/api.ts](../frontend/src/api.ts) | fetch and Authorization | Client requests use /api/v1 and optionally a bearer token |
| [app/main.py](../app/main.py) | include_router and health routes | API registration and readiness checks |
| [app/db/session.py](../app/db/session.py) | get_db, commit, rollback | The request dependency owns transaction completion |

Addresses depend on where the caller runs. From your browser, localhost means your Windows computer. From the API container, db means the PostgreSQL service on the Compose network; localhost would refer to that API container itself. Local ports 3000 and 8000 are bound to loopback. This is a local development deployment.

## 5. Understand registration and login before editing tasks

Registration sends an email, password, and full name to POST /api/v1/auth/register. Pydantic validates the fields. The auth service normalizes the email and stores an Argon2id password hash. The database enforces unique email. A password hash allows verification without saving the original password.

Login sends credentials to POST /api/v1/auth/login. The Redis-backed login limiter runs first. The auth service verifies the password and returns a signed JWT access token. The frontend keeps that token in sessionStorage for the browser session. Later calls attach Authorization: Bearer followed by the token.

For protected routes, app/api/dependencies.py checks the token and loads an active user. Workspace membership checks then decide whether that user may access the resource. A signed token is identity evidence; it is not permission to read any task UUID.

Read [auth routes](../app/api/v1/auth.py), [auth service](../app/services/auth.py), [security helpers](../app/core/security.py), and [request dependencies](../app/api/dependencies.py). Then inspect one successful request in the browser Network panel. Keep its token private.

There is no refresh-token or token-revocation system in this version. Logout clears the browser's token and query state; a copied access token can remain valid until expiry unless another validation condition changes. Do not describe this app as using HTTP-only session cookies.

## 6. Follow a task update from beginning to end

Open [map 2](diagrams/02-task-edit.html), then trace this example: change a task from todo to in_progress.

1. TaskPanel keeps the task snapshot the user opened, including its version.
2. Saving builds a PATCH body with changed fields and expected_version.
3. api.ts serializes JSON, attaches the token, and calls /api/v1/tasks/{id} through nginx.
4. FastAPI validates TaskUpdate and resolves the active user and database session.
5. The task service loads the task through workspace membership.
6. It locks the workspace row, then rechecks membership after waiting. A user removed during the wait must not retain old permission.
7. It verifies the editing role and validates a changed assignee against workspace membership.
8. SQL updates the row only if its current version equals expected_version. A successful update increments the version.
9. The service appends task.updated activity in the same transaction and refreshes the returned task.
10. get_db commits before the response leaves the request dependency scope. Exceptions roll back the transaction.
11. The browser receives the result, refreshes affected queries, and shows the current data.

The code path is [TaskPanel.tsx](../frontend/src/TaskPanel.tsx) → [api.ts](../frontend/src/api.ts) → [task route](../app/api/v1/tasks.py) → [task service](../app/services/tasks.py) → [session dependency](../app/db/session.py). In the source, search for expected_version, update_task, lock_workspace, record_event, and commit.

Example body; replace the URL ID with an actual task UUID and use its current version:

```json
{
  "status": "in_progress",
  "expected_version": 1
}
```

Why the version matters: Alex and Priya both open version 1. Alex saves, producing version 2. Priya still submits expected_version 1. Her update affects zero rows, so the API returns 409 rather than overwriting Alex's work. The UI preserves the draft and offers Load latest version. Review the new version before saving again.

The workspace lock coordinates membership and task writes, but it serializes writes within that workspace. The version predicate detects stale client snapshots even when database operations wait and execute sequentially. These solve related but different correctness problems.

Try it: open the same task in two tabs, change it in one, then submit the older editor. Explain the 409 using the diagram. Do this with a learning task, because the successful edit changes real stored data.

## 7. Understand the data model behind the arrows

The ownership chain is User → Membership → Workspace → Project → Task. One user can join several workspaces; memberships carry roles. Tasks can have comments, activity records, and notification-delivery records.

Read [app/models/__init__.py](../app/models/__init__.py). Find these actual constraints:

- Membership's composite key prevents duplicate membership in the same workspace.
- A task's project/workspace pair must refer to a project in that workspace.
- A task's assignee/workspace pair must refer to a workspace membership.
- A notification's unique key identifies its task, recipient, reminder kind, and due occurrence.

API checks provide understandable failures; database constraints protect stored relationships even if another writer bypasses the API. UUIDs identify resources and do not replace permissions.

The backend does not have a separate repository abstraction layer. Routes and services use SQLAlchemy directly. Avoid inventing layers when explaining the project.

## 8. Follow reminders independently of the browser

Open [map 3](diagrams/03-reminders.html). Creating or editing a task is a normal request. A later reminder follows a different path:

1. Celery beat publishes a scan message every 60 seconds.
2. A Celery worker consumes that message from Redis.
3. schedule_reminders queries unfinished tasks due within one hour or already overdue.
4. It creates deduplicated delivery records in PostgreSQL, claims eligible records, and commits queued state with a five-minute lease.
5. The scan task publishes delivery IDs to Redis. A worker later consumes each delivery job.
6. The delivery service locks the delivery row and reloads current task and recipient data.
7. A done task, changed due date, changed recipient, or inactive recipient can cancel delivery.
8. An eligible record goes through the email adapter. Console mode logs its delivery ID. SMTP mode contacts the configured mail server.
9. The outcome is recorded. Transient failures schedule backoff; at most five recorded send attempts are allowed.

Read [beat configuration](../app/workers/celery_app.py), [worker tasks](../app/workers/reminders.py), and [notification service](../app/services/notifications.py). Beat schedules; workers execute; Redis transports; PostgreSQL stores durable delivery intent and outcomes.

If publishing fails after the database commits, a later scan can reclaim an expired queued lease. If SMTP accepts mail and the process crashes before success is saved, retry can send twice. The design reduces duplicates but does not guarantee exactly-once email delivery. A successful console record is not evidence of an inbox delivery.

To observe without changing code, from BACKEND:

```powershell
docker compose logs --tail 80 worker beat
```

To run an experiment, assign a due date within 30 minutes to a disposable unfinished task and wait for the scan. Match a logged delivery ID to the stored delivery record. Keep console mode labelled as development delivery.

## 9. Understand Archify itself

Open [map 4](diagrams/04-how-archify-works.html). The process used here was:

1. Read the real application source and select a question, such as where a task is saved.
2. Choose a diagram type: architecture for components; sequence for ordered calls.
3. Author typed JSON with components or participants, relationships, labels, notes, and positions.
4. Run the CLI finalize command against that JSON and an output path.
5. Validation checks schema and layout. Delivery renders and publishes the artifact with metadata. Strict checks and browser checks verify the delivered output.
6. Read the receipt. A failed gate requires a focused repair and another run; nonzero exit is not success.
7. Open the HTML, explore it, and revise JSON when the explanation needs to change.

Archify supplies the schemas, renderers, viewer, and checks. The coding agent supplies interpretation and diagram content. Downloading Archify does not automatically analyze TaskFlow, and the CLI is not a separate hosted AI service. Layout validation cannot prove every claim about your application; you must compare diagrams with the actual code.

For implementation exploration, start at [CLI entry](../archify/archify/bin/archify.mjs), find commandFinalize, then follow [bin/finalize.mjs](../archify/archify/bin/finalize.mjs). FINALIZE_STAGES names validate, deliver, check, and browser-check. The [architecture schema](../archify/archify/schemas/architecture.schema.json) explains allowed fields; the [skill](../archify/archify/SKILL.md) explains the authoring workflow. Do not read the entire CLI before understanding one diagram source.

## 10. Edit your first diagram and regenerate it

Node.js 18 or later is required by this downloaded version. Check your installed version with node --version. The skill CLI can generate these diagrams without installing the root contributor test dependencies.

Open sources/01-taskflow-map.json. Find the Task services component and change its sublabel to a short accurate phrase. Keep IDs stable so existing relationships continue to refer to the same components. This only edits learning material; it does not change TaskFlow behavior.

From BACKEND in PowerShell:

```powershell
node archify/archify/bin/archify.mjs finalize architecture archify-learning/sources/01-taskflow-map.json archify-learning/diagrams/01-taskflow-map.html --quality showcase --out-dir archify-learning/reviews/my-first-edit --json
```

Use a new review directory name for each later delivery to the same HTML path, so previous browser evidence stays associated with the output it checked. Wait for completion. Check that ok is true and the four gates say pass, then reopen the HTML. Do not treat a half-completed command or an earlier passing receipt as proof for your new edit.

To rebuild all four edited JSON sources, run:

```powershell
powershell -NoProfile -File archify-learning/rebuild.ps1
```

build_sources.py recreates the original sources and overwrites your JSON edits. Run it only when you intentionally want to reset those diagrams. rebuild.ps1 renders the existing JSON; it preserves your edits. If Windows execution policy blocks the script, run the individual Node command above rather than changing your machine-wide policy.

Example request for a future coding-agent session: "Read BACKEND/app/services/tasks.py and the request dependency, then use the downloaded Archify skill to update the task-edit diagram. Preserve the stale-version failure and explain when commit happens. Cite only source files that support each claim."

## 11. Connect development to deployment

The existing [project handbook](../docs/TASKFLOW_HANDBOOK.md) provides the longer development and interview course. The [deployment companion](../docs/deployment/README.md) contains the exact single-Linux-server example and commands. Public deployment was not performed as part of this learning pack.

The complete release sequence is: define the behavior → change schema/service/UI as needed → apply a reviewed migration → run relevant tests → build frontend and images → configure server/DNS/secrets → run the release migration once → start services → verify public HTTPS and application flows → verify backup restoration → record the revision and release result.

In the example public topology, the browser reaches Caddy over HTTPS, Caddy forwards to nginx, and nginx forwards API calls to FastAPI. API, worker, and beat share private network access to PostgreSQL and Redis. Only Caddy publishes public ports 80 and 443. This topology is provided configuration, not a claim that a public service is already running.

Before using it publicly, follow the companion's release adjustments, including the API documentation link currently pointing to localhost in App.tsx. Set real secrets, configure proxy trust, and verify DNS/TLS. Use console email only when it is clearly described as a demo. Do not assume that a local build proves production capacity or backup recovery.

CI lives in the parent DSA_DOJO/.github/workflows/taskflow-ci.yml. It validates builds and backend checks; it does not automatically provision a public server. The earlier project verification recorded 62 passing backend tests. Those are existing project results, not newly executed application tests for this diagram-only change.

## 12. Practice explaining the project professionally

Use this short explanation after you can trace it yourself: "TaskFlow is a workspace-based task application. React calls a FastAPI API through nginx. The backend checks identity, membership, and editing rules, then stores task changes and activity together in PostgreSQL. Expected versions reject stale edits. Celery beat and workers use Redis to run reminders outside the request. Docker packages the local stack."

Answer these questions while pointing at a map:

| Question | A strong answer identifies |
| --- | --- |
| Why can React not write directly to PostgreSQL? | API ownership of validation and authorization; database credentials stay server-side |
| Why use both transactions and a version field? | Atomic task/activity changes versus detection of stale client snapshots |
| Why recheck membership after locking? | Permission may have changed while the request waited |
| Is Redis the task database? | No; PostgreSQL owns task records and Redis handles the broker and login counter |
| What does beat do differently from a worker? | Beat schedules messages; a worker executes them |
| Is a reminder guaranteed exactly once? | No; explain the crash window after SMTP acceptance |
| Does Archify verify that the application works? | It checks the diagram artifact; application tests and real behavior require their own evidence |
| Is the app publicly deployed? | Local stack is running; public deployment must be performed and verified separately |

For your first learning week: day 1 open the maps and run the app; day 2 trace registration/login; day 3 trace one task read; day 4 trace one task edit; day 5 reproduce a version conflict; day 6 explain a reminder; day 7 give a two-minute explanation without reading. Repeat a day if you cannot explain its arrows.

Your practical finish line is being able to open the responsible file for any important arrow, show the corresponding request or test, and explain one limitation. The diagrams are a navigation aid; understanding comes from checking them against the program.

## 13. Verification and maintenance

The four diagram deliveries have automated validation, delivery, artifact, and real-browser check receipts. They test generated diagrams, not TaskFlow's public deployment. Diagram 4 pins upstream source evidence to the downloaded commit; maps 1–3 use the local working-tree manifest instead of false commit claims.

If the application changes, re-read affected files and update the diagrams and guide together. The manifest contains SHA-256 hashes of the inspected files, which can identify drift; it does not automatically keep explanations correct. Preserve the upstream MIT license when sharing Archify code. Keep secrets, private tokens, database dumps, and .env files out of diagrams and shared bundles.
