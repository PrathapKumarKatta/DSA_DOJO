from uuid import uuid4

import pytest


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("get", "/tasks/{task}", None),
        ("patch", "/tasks/{task}", {"expected_version": 1, "title": "Stolen"}),
        ("delete", "/tasks/{task}", None),
        ("post", "/tasks/{task}/comments", {"body": "Intruder"}),
        ("get", "/tasks/{task}/comments", None),
        ("get", "/tasks/{task}/activity", None),
        ("get", "/projects/{project}/tasks", None),
        ("post", "/projects/{project}/tasks", {"title": "Intruder"}),
        ("get", "/workspaces/{workspace}/stats", None),
        ("get", "/workspaces/{workspace}/members", None),
        ("get", "/workspaces/{workspace}/activity", None),
        ("post", "/workspaces/{workspace}/projects", {"name": "Intruder"}),
    ],
)
async def test_cross_tenant_isolation(client, actors, task, method, path, payload):
    path = path.format(
        task=task["id"], project=actors["project"]["id"], workspace=actors["workspace"]["id"]
    )
    kwargs = {"headers": actors["outsider"]["headers"]}
    if payload is not None:
        kwargs["json"] = payload
    assert (await client.request(method, "/api/v1" + path, **kwargs)).status_code == 404


async def test_workspace_list_is_scoped(client, actors):
    for role, count in (("owner", 1), ("outsider", 0)):
        result = await client.get("/api/v1/workspaces", headers=actors[role]["headers"])
        assert result.json()["total"] == count


@pytest.mark.parametrize("role,expected", [("owner", 201), ("admin", 201), ("member", 403)])
async def test_project_creation_roles(client, actors, role, expected):
    result = await client.post(
        f"/api/v1/workspaces/{actors['workspace']['id']}/projects",
        json={"name": "Project"},
        headers=actors[role]["headers"],
    )
    assert result.status_code == expected


@pytest.mark.parametrize(
    "role,expected", [("owner", 200), ("admin", 200), ("member", 200), ("other", 403)]
)
async def test_task_edit_roles(client, actors, task, role, expected):
    result = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"expected_version": 1, "status": "done"},
        headers=actors[role]["headers"],
    )
    assert result.status_code == expected


async def test_member_creation_and_admin_limits(client, actors):
    wid = actors["workspace"]["id"]
    headers = actors["admin"]["headers"]
    for role in ("owner", "admin"):
        result = await client.post(
            f"/api/v1/workspaces/{wid}/members",
            json={"user_id": actors["outsider"]["id"], "role": role},
            headers=headers,
        )
        assert result.status_code == 403
    result = await client.post(
        f"/api/v1/workspaces/{wid}/members", json={"user_id": str(uuid4())}, headers=headers
    )
    assert result.status_code == 404
    assert (await client.delete(f"/api/v1/workspaces/{wid}", headers=headers)).status_code == 403
    assert (
        await client.delete(
            f"/api/v1/workspaces/{wid}/members/{actors['owner']['id']}", headers=headers
        )
    ).status_code == 403
    result = await client.post(
        f"/api/v1/projects/{actors['project']['id']}/tasks",
        json={"title": "My task"},
        headers=actors["member"]["headers"],
    )
    assert result.status_code == 201
    assert (
        await client.delete(
            f"/api/v1/tasks/{result.json()['id']}", headers=actors["member"]["headers"]
        )
    ).status_code == 204


async def test_member_removal_unassigns_and_revokes_access(client, actors, task):
    wid = actors["workspace"]["id"]
    headers = actors["owner"]["headers"]
    assert (
        await client.delete(
            f"/api/v1/workspaces/{wid}/members/{actors['member']['id']}", headers=headers
        )
    ).status_code == 204
    result = (await client.get(f"/api/v1/tasks/{task['id']}", headers=headers)).json()
    assert result["assignee_id"] is None
    assert result["version"] == 2
    events = (await client.get(f"/api/v1/tasks/{task['id']}/activity", headers=headers)).json()
    assert events["items"][0]["action"] == "task.unassigned"
    assert (
        await client.get(f"/api/v1/tasks/{task['id']}", headers=actors["member"]["headers"])
    ).status_code == 404


async def test_workspace_owner_delete_cascades(client, actors, task):
    result = await client.delete(
        f"/api/v1/workspaces/{actors['workspace']['id']}", headers=actors["owner"]["headers"]
    )
    assert result.status_code == 204, result.text
    assert (
        await client.get(f"/api/v1/tasks/{task['id']}", headers=actors["owner"]["headers"])
    ).status_code == 404
