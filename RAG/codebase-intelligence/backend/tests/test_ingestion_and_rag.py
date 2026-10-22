from pathlib import Path
import time
import uuid
from fastapi.testclient import TestClient


def test_full_ingestion_and_rag_pipeline(client: TestClient):
    unique_id = uuid.uuid4().hex[:8]
    email = f"lead_dev_{unique_id}@example.com"
    password = "DevPassword123!"

    # 1. Register and Login
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Project
    proj_res = client.post("/api/v1/projects", json={"name": "Microservice Project"}, headers=headers)
    assert proj_res.status_code == 201
    project_id = proj_res.json()["id"]

    # 3. Upload ZIP file
    zip_sample_path = Path("/Users/charan/RAG/sample_projects/microservice.zip")
    assert zip_sample_path.exists(), "Sample ZIP archive must exist"

    with open(zip_sample_path, "rb") as zf:
        upload_res = client.post(
            f"/api/v1/projects/{project_id}/upload",
            files={"file": ("microservice.zip", zf, "application/zip")},
            headers=headers,
        )
    assert upload_res.status_code == 202
    job_id = upload_res.json()["id"]
    assert job_id is not None

    # 4. Wait / Execute Ingestion pipeline directly to guarantee synchronous completion for test
    # (If background task already picked it up or in progress, we can inspect status)
    for _ in range(30):
        status_res = client.get(f"/api/v1/projects/{project_id}/status", headers=headers)
        if status_res.json()["project_status"] == "ready":
            break
        time.sleep(0.5)

    status_data = client.get(f"/api/v1/projects/{project_id}/status", headers=headers).json()
    assert status_data["project_status"] == "ready"
    assert status_data["active_job"]["status"] == "completed"
    assert status_data["active_job"]["processed_files"] >= 5

    # 5. List Files
    files_res = client.get(f"/api/v1/projects/{project_id}/files", headers=headers)
    assert files_res.status_code == 200
    files_data = files_res.json()
    assert files_data["total"] >= 5
    file_paths = [f["path"] for f in files_data["items"]]
    assert any("auth/service.py" in p for p in file_paths)
    assert any("db/connection.py" in p for p in file_paths)

    # 6. Retrieve single file content
    auth_file = next(f for f in files_data["items"] if "auth/service.py" in f["path"])
    file_detail = client.get(
        f"/api/v1/projects/{project_id}/files/{auth_file['id']}", headers=headers
    )
    assert file_detail.status_code == 200
    assert "def authenticate_user" in file_detail.json()["content"]

    # 7. Search Codebase
    search_res = client.post(
        f"/api/v1/projects/{project_id}/search",
        json={"query": "authenticate_user", "top_k": 3},
        headers=headers,
    )
    assert search_res.status_code == 200
    search_hits = search_res.json()["results"]
    assert len(search_hits) > 0
    assert any("auth/service.py" in h["file_path"] for h in search_hits)

    # 8. Chat with Codebase (RAG)
    chat_res = client.post(
        f"/api/v1/projects/{project_id}/chat",
        json={"message": "Where is user authentication implemented?"},
        headers=headers,
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()
    conv_id = chat_data["conversation_id"]
    assistant_msg = chat_data["message"]
    assert assistant_msg["role"] == "assistant"
    assert len(assistant_msg["citations"]) > 0
    assert any("auth/service.py" in c["file_path"] for c in assistant_msg["citations"])

    # 9. Verify Conversation History
    history_res = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
    assert history_res.status_code == 200
    messages = history_res.json()["messages"]
    assert len(messages) == 2  # user message + assistant message
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
