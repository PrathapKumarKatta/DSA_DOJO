import uuid
from fastapi.testclient import TestClient


def test_health_endpoints(client: TestClient):
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "ok"

    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    data = ready_res.json()
    assert data["database"] == "connected"
    assert data["redis"] == "connected"


def test_auth_and_project_lifecycle(client: TestClient):
    unique_suffix = uuid.uuid4().hex[:8]
    email_a = f"developer_a_{unique_suffix}@example.com"
    email_b = f"developer_b_{unique_suffix}@example.com"
    password = "SuperSecretPassword123!"

    # 1. Register User A
    res = client.post("/api/v1/auth/register", json={"email": email_a, "password": password})
    assert res.status_code == 201, res.text
    user_a_data = res.json()
    assert user_a_data["email"] == email_a

    # 2. Duplicate registration should fail
    dup_res = client.post("/api/v1/auth/register", json={"email": email_a, "password": password})
    assert dup_res.status_code == 400

    # 3. Login with wrong password
    bad_login = client.post("/api/v1/auth/login", json={"email": email_a, "password": "wrongpassword"})
    assert bad_login.status_code == 401

    # 4. Login User A
    login_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": password})
    assert login_a.status_code == 200
    token_a = login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 5. Access /auth/me for User A
    me_a = client.get("/api/v1/auth/me", headers=headers_a)
    assert me_a.status_code == 200
    assert me_a.json()["id"] == user_a_data["id"]

    # 6. User A creates a project
    proj_res = client.post("/api/v1/projects", json={"name": "Alpha Repo"}, headers=headers_a)
    assert proj_res.status_code == 201
    project_a = proj_res.json()
    project_a_id = project_a["id"]
    assert project_a["name"] == "Alpha Repo"

    # 7. User A lists projects
    list_a = client.get("/api/v1/projects", headers=headers_a)
    assert list_a.status_code == 200
    assert any(p["id"] == project_a_id for p in list_a.json()["items"])

    # 8. Register and login User B
    client.post("/api/v1/auth/register", json={"email": email_b, "password": password})
    login_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": password})
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 9. Tenant Isolation: User B cannot access User A's project
    res_b_access = client.get(f"/api/v1/projects/{project_a_id}", headers=headers_b)
    assert res_b_access.status_code == 404

    # 10. Tenant Isolation: User B's project list does NOT contain User A's project
    list_b = client.get("/api/v1/projects", headers=headers_b)
    assert list_b.status_code == 200
    assert not any(p["id"] == project_a_id for p in list_b.json()["items"])

    # 11. Tenant Isolation: User B cannot delete User A's project
    res_b_delete = client.delete(f"/api/v1/projects/{project_a_id}", headers=headers_b)
    assert res_b_delete.status_code == 404
