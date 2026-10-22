"""Exercise the running local stack using the bundled public sample project.

Run from the repository root with Python and httpx installed. Credentials are
generated into an ignored local file and are never printed to the terminal.
"""
import json
from pathlib import Path
import secrets
import time
from zipfile import ZipFile, ZIP_DEFLATED

import httpx

ROOT = Path(__file__).resolve().parents[1]
state_file = ROOT / '.local-demo.json'
state = json.loads(state_file.read_text()) if state_file.exists() else {
    'email': f'local-demo-{secrets.token_hex(4)}@example.com',
    'password': secrets.token_urlsafe(24),
}
state_file.write_text(json.dumps(state, indent=2)+'\n')

with httpx.Client(base_url='http://127.0.0.1:3002', timeout=180) as client:
    ready = client.get('/health/ready')
    ready.raise_for_status()
    assert ready.json()['status'] == 'ready'
    print('Frontend proxy, PostgreSQL and Redis readiness passed.', flush=True)
    register = client.post('/api/v1/auth/register', json={k:state[k] for k in ['email','password']})
    assert register.status_code in (201, 400, 409), f'Registration failed: {register.status_code}'
    login = client.post('/api/v1/auth/login', json={k:state[k] for k in ['email','password']})
    login.raise_for_status()
    client.headers['Authorization'] = 'Bearer '+login.json()['access_token']
    me = client.get('/api/v1/auth/me')
    me.raise_for_status()
    assert me.json()['email'] == state['email']
    print('Registration and login passed; credentials saved privately in .local-demo.json.', flush=True)

    if 'project_id' not in state:
        project = client.post('/api/v1/projects', json={'name':'Sample microservice — local verification'})
        project.raise_for_status()
        state['project_id'] = project.json()['id']
        state_file.write_text(json.dumps(state, indent=2)+'\n')
    project_id = state['project_id']
    status = client.get(f'/api/v1/projects/{project_id}/status').json()
    archive = ROOT/'sample_projects'/'microservice.zip'
    with ZipFile(archive, 'w', ZIP_DEFLATED) as z:
        for file in sorted((ROOT/'sample_projects'/'microservice').rglob('*')):
            if file.is_file():
                z.write(file, file.relative_to(ROOT/'sample_projects'/'microservice'))
    if status['project_status'] not in ('processing','ready'):
        with archive.open('rb') as f:
            upload = client.post(f'/api/v1/projects/{project_id}/upload',files={'file':('microservice.zip',f,'application/zip')})
        upload.raise_for_status()
        print('Sample ZIP accepted by the running ingestion API.', flush=True)
    deadline = time.monotonic()+900
    previous = None
    while time.monotonic()<deadline:
        response=client.get(f'/api/v1/projects/{project_id}/status')
        response.raise_for_status()
        status=response.json()
        progress=(status['project_status'],(status.get('active_job') or {}).get('processed_files'))
        if progress != previous:
            print(f'Indexing state: {progress[0]}, files processed: {progress[1]}',flush=True)
            previous=progress
        if status['project_status']=='ready': break
        if status['project_status']=='failed':
            raise RuntimeError('Indexing failed: '+str((status.get('active_job') or {}).get('error_message')))
        time.sleep(3)
    else: raise TimeoutError('Indexing did not finish within 15 minutes; inspect worker logs.')
    files=client.get(f'/api/v1/projects/{project_id}/files')
    files.raise_for_status()
    assert files.json()['total']>0
    question='How does the database connection work?'
    search=client.post(f'/api/v1/projects/{project_id}/search',json={'query':question,'top_k':5})
    search.raise_for_status()
    assert search.json()['total']>0
    answer=client.post(f'/api/v1/projects/{project_id}/chat',json={'message':question,'top_k':5})
    answer.raise_for_status()
    citations=answer.json()['message']['citations']
    assert citations, 'Expected source citations in the configured mock answer.'
    print(f"Verified {files.json()['total']} indexed files, {search.json()['total']} retrieval results and {len(citations)} chat citations.",flush=True)
    print('Full local flow passed. Answer generation uses the configured mock provider.',flush=True)
