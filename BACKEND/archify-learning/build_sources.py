"""Build editable Archify diagrams from the inspected TaskFlow working tree.

Run from BACKEND with Python. Rendering is a separate step in rebuild.ps1.
No application code or database state is modified.
"""
import hashlib
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
(HERE / 'sources').mkdir(exist_ok=True)
(HERE / 'diagrams').mkdir(exist_ok=True)


def card(title, *items, dot='cyan'):
    return dict(dot=dot, title=title, items=list(items))


def node(id, type, label, sublabel, x, y, w=172, h=64, **extra):
    return dict(id=id, type=type, label=label, sublabel=sublabel,
                pos=[x, y], size=[w, h], **extra)


def edge(id, a, b, label, variant='default'):
    return dict(id=id, **{'from': a, 'to': b}, label=label, variant=variant)


def save(slug, title, components, connections, cards, **meta):
    data = dict(schema_version=1, diagram_type='architecture',
                meta=dict(title=title, output=f'archify-learning/diagrams/{slug}.html',
                          locale='en', quality_profile='showcase', **meta),
                components=components, connections=connections, cards=cards)
    (HERE / 'sources' / f'{slug}.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


save('01-taskflow-map', 'TaskFlow | From browser to stored tasks', [
    node('browser', 'frontend', 'React in browser', 'Forms and Query cache', 40, 40),
    node('nginx', 'cloud', 'nginx frontend', 'Serves JS and proxies API', 370, 40),
    node('api', 'backend', 'FastAPI', 'JWT and schema checks', 700, 40),
    node('services', 'backend', 'Task services', 'Membership and version', 700, 260),
    node('db', 'database', 'PostgreSQL', 'Tasks and activity', 370, 260),
    node('redis', 'messagebus', 'Redis', 'Login attempt counter', 1030, 40),
], [
    edge('http', 'browser', 'nginx', 'HTTP /api/v1', 'emphasis'),
    edge('proxy', 'nginx', 'api', 'proxy HTTP', 'emphasis'),
    edge('invoke', 'api', 'services', 'protected task call', 'security'),
    edge('sql', 'services', 'db', 'SQL transaction', 'emphasis'),
    edge('limiter', 'api', 'redis', 'login only'),
], [
    card('Read the arrows', 'The browser runs React; nginx serves its compiled assets.',
         'Protected task requests pass JWT checks and workspace membership checks.',
         'The response returns over the same HTTP connection; reply arrows are omitted.'),
    card('Persistence', 'PostgreSQL is the task source of truth.',
         'Task edits and their activity records commit in one transaction.',
         'Redis is not a read-through task cache in this application.', dot='emerald'),
    card('Scope', 'Local Docker configuration, not a public deployment.',
         'Worker and beat are explained in map 03.',
         'Current working-tree summary; source locations are in the companion guide.', dot='amber'),
])

# A sequence is ordered interaction, not measured latency. nginx is folded into transport.
seq = dict(schema_version=1, diagram_type='sequence',
           meta=dict(title='TaskFlow | One task edit from click to commit',
                     output='archify-learning/diagrams/02-task-edit.html',
                     locale='en', quality_profile='showcase'),
           participants=[dict(id=i, type=t, label=l, sublabel=s) for i,t,l,s in [
               ('ui','frontend','React UI','TaskPanel and api.ts'),
               ('api','backend','FastAPI','route and dependencies'),
               ('service','backend','Task service','authorization and update'),
               ('db','database','PostgreSQL','transaction and version')]],
           messages=[], cards=[
               card('Success', 'The client submits expected_version with its changed fields.',
                    'The service locks the workspace and rechecks permissions after waiting.',
                    'The SQL update matches the expected version; activity joins the transaction.'),
               card('Conflict and errors', 'A stale expected_version affects no row and returns 409.',
                    'The dependency rolls back exceptions; 200 follows a successful commit.',
                    'The UI retains a stale draft and offers Load latest version.', dot='rose'),
               card('How to read', 'Read top to bottom. Positions indicate order, not duration.',
                    'This is the successful branch; error branches are described in these cards.',
                    'nginx transport and low-level SQL round trips are intentionally folded.', dot='amber')])
steps = [
    ('ui','api','PATCH task + expected_version','emphasis'),
    ('api','db','validate JWT; load active user','security'),
    ('db','api','user found','return'),
    ('api','service','validated TaskUpdate','default'),
    ('service','db','load task through membership','security'),
    ('db','service','task and membership','return'),
    ('service','db','lock workspace; recheck access','security'),
    ('db','service','current authorization','return'),
    ('service','db','UPDATE WHERE version matches','emphasis'),
    ('db','service','one updated row','return'),
    ('service','db','insert activity; flush and refresh','default'),
    ('service','api','updated task','return'),
    ('api','db','dependency commits transaction','emphasis'),
    ('db','api','commit succeeds','return'),
    ('api','ui','200 JSON; invalidate task queries','return'),
]
for k,(a,b,label,variant) in enumerate(steps):
    seq['messages'].append(dict(id=f'step-{k+1}', **{'from':a,'to':b},
                                y=170+k*38, label=label, variant=variant))
(HERE/'sources'/'02-task-edit.json').write_text(json.dumps(seq,indent=2)+'\n',encoding='utf-8')

save('03-reminders', 'TaskFlow | Reminders run outside the HTTP request', [
    node('beat', 'backend', 'Celery beat', 'Schedules scan every 60s', 40, 40),
    node('redis', 'messagebus', 'Redis broker', 'Scan and delivery messages', 390, 40),
    node('worker', 'backend', 'Celery worker', 'Executes scan and deliver', 740, 40),
    node('db', 'database', 'PostgreSQL', 'Due tasks and delivery rows', 740, 280),
    node('email', 'external', 'Email adapter', 'Console or configured SMTP', 1090, 40),
], [
    edge('schedule', 'beat','redis','enqueue scan','dashed'),
    edge('consume','redis','worker','consume jobs','dashed'),
    edge('records','worker','db','claim and record'),
    edge('send','worker','email','if still eligible'),
    edge('enqueue-delivery','worker','redis','enqueue delivery','dashed'),
], [
    card('Scheduling', 'Beat queues a scan; a worker executes that scan.',
         'The scanner finds unfinished tasks due within one hour or already overdue.',
         'Recipient is the assignee, falling back to the creator.'),
    card('Durable intent', 'PostgreSQL records each task/recipient/due occurrence.',
         'Expired five-minute queue leases allow dispatch recovery.',
         'A delivery reloads current data and can cancel an obsolete reminder.', dot='emerald'),
    card('Delivery limits', 'Transient errors back off; at most five recorded send attempts.',
         'Console delivery logs an ID; it does not send to an inbox.',
         'SMTP success before a process crash can still cause a duplicate retry.', dot='rose'),
])

revision = subprocess.check_output(['git','-C',str(ROOT/'archify'),'rev-parse','HEAD'],text=True).strip()
# This diagram has commit-verified source cards because the downloaded upstream is clean.
def src(path, first, last):
    return [dict(path=path, line=first, end_line=last)]
save('04-how-archify-works', 'Archify | From explanation to interactive HTML', [
    node('agent','external','Your coding agent','Reads intent and source',40,40,
         sources=src('archify/SKILL.md',36,38)),
    node('json','database','Typed JSON file','Editable diagram source',370,40,
         sources=src('archify/schemas/architecture.schema.json',1,30)),
    node('finalize','backend','Finalize CLI','Coordinates quality gates',700,40,
         sources=src('archify/bin/archify.mjs',5888,5955)),
    node('gates','security','Validation and delivery','Check before accepting',700,280,
         sources=src('archify/SKILL.md',39,49)),
    node('html','frontend','Standalone HTML','Explore in your browser',370,280,
         sources=src('archify/SKILL.md',1,12)),
], [
    edge('author','agent','json','authors'),
    edge('input','json','finalize','reads'),
    edge('run','finalize','gates','runs checks'),
    edge('publish','gates','html','on passing gates','emphasis'),
], [
    card('Who does what', 'The coding agent interprets the project and authors JSON.',
         'The CLI renders and checks that source; it does not independently understand your whole app.',
         'A diagram can pass layout checks while still making a factual mistake.'),
    card('Artifacts', 'Keep JSON for editing and HTML for viewing.',
         'Delivery and finalize receipts record automated verification.',
         'HTML viewing needs no running TaskFlow database or API.', dot='emerald'),
    card('Source-backed map', 'This map cites the downloaded Archify commit.',
         'TaskFlow maps summarize uncommitted local code and have a separate source manifest.',
         'No global skill installation was performed.', dot='amber'),
], repository=dict(url='https://github.com/tt-a1i/archify.git',revision=revision))

paths = ['compose.yaml','frontend/nginx.conf','frontend/src/api.ts','frontend/src/TaskPanel.tsx',
         'frontend/src/App.tsx','app/main.py','app/api/dependencies.py','app/api/v1/tasks.py',
         'app/db/session.py','app/services/tasks.py','app/services/permissions.py',
         'app/services/notifications.py','app/workers/celery_app.py','app/workers/reminders.py',
         'app/models/__init__.py','docs/deployment/compose.production.yaml']
manifest = dict(scope='TaskFlow current local working tree; not pinned to a Git commit',
                archify_revision=revision, files=[])
for rel in paths:
    p=ROOT/rel
    manifest['files'].append(dict(path=rel,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                                  lines=len(p.read_text(encoding='utf-8').splitlines())))
(HERE/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Created four editable diagrams and a local source manifest.')
