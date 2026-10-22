import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select

from app.models import ActivityEvent, Task


async def test_task_lifecycle_comments_audit(client, actors, task):
    headers = actors["owner"]["headers"]
    path = f"/api/v1/tasks/{task['id']}"
    assert task["version"] == 1
    result = await client.patch(
        path,
        json={"expected_version": 1, "status": "in_progress", "assignee_id": None},
        headers=headers,
    )
    assert result.status_code == 200
    assert result.json()["version"] == 2
    assert result.json()["assignee_id"] is None
    assert (
        await client.post(path + "/comments", json={"body": "Looks good"}, headers=headers)
    ).status_code == 201
    comments = (await client.get(path + "/comments", headers=headers)).json()
    assert comments["items"][0]["body"] == "Looks good"
    events = (await client.get(path + "/activity", headers=headers)).json()
    assert {item["action"] for item in events["items"]} == {
        "task.created",
        "task.updated",
        "comment.created",
    }
    assert (await client.delete(path, headers=headers)).status_code == 204
    events = (
        await client.get(
            f"/api/v1/workspaces/{actors['workspace']['id']}/activity", headers=headers
        )
    ).json()
    assert any(
        e["action"] == "task.deleted" and e["payload"]["task_id"] == task["id"]
        for e in events["items"]
    )
    assert (await client.get(path, headers=headers)).status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "invalid"},
        {"title": ""},
        {"title": " "},
        {"title": "x" * 201},
        {"due_at": "2026-11-01T12:00:00"},
        {"priority": "critical"},
        {"creator_id": "bad"},
    ],
)
async def test_task_validation(client, actors, payload):
    result = await client.post(
        f"/api/v1/projects/{actors['project']['id']}/tasks",
        json={"title": "Valid"} | payload,
        headers=actors["owner"]["headers"],
    )
    assert result.status_code == 422


@pytest.mark.parametrize("payload", [{"title": None}, {"status": None}, {"description": None}, {}])
async def test_patch_null_and_empty_rejected(client, actors, task, payload):
    result = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"expected_version": 1} | payload,
        headers=actors["owner"]["headers"],
    )
    assert result.status_code == 422


async def test_assignment_validation_rolls_back(client, actors, task, factory):
    result = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={
            "expected_version": 1,
            "title": "Must roll back",
            "assignee_id": actors["outsider"]["id"],
        },
        headers=actors["owner"]["headers"],
    )
    assert result.status_code == 422
    async with factory() as db:
        saved = await db.get(Task, UUID(task["id"]))
        assert saved.title == "Build API" and saved.version == 1
        assert await db.scalar(select(func.count()).select_from(ActivityEvent)) == 1


async def test_real_concurrent_updates(client, actors, task, factory):
    path = f"/api/v1/tasks/{task['id']}"
    results = await asyncio.gather(
        *[
            client.patch(
                path,
                json={"expected_version": 1, "title": title},
                headers=actors["owner"]["headers"],
            )
            for title in ("First update", "Second update")
        ]
    )
    assert sorted(result.status_code for result in results) == [200, 409]
    async with factory() as db:
        assert (
            await db.scalar(
                select(func.count())
                .select_from(ActivityEvent)
                .where(ActivityEvent.action == "task.updated")
            )
            == 1
        )


async def test_filters_search_pagination_stats(client, actors, task):
    headers = actors["owner"]["headers"]
    path = f"/api/v1/projects/{actors['project']['id']}/tasks"
    for title, status, priority in (
        ("100% coverage", "blocked", "urgent"),
        ("Another task", "done", "low"),
    ):
        result = await client.post(
            path,
            json={
                "title": title,
                "status": status,
                "priority": priority,
                "due_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            },
            headers=headers,
        )
        assert result.status_code == 201
    for query, count in (
        ("status=blocked", 1),
        ("priority=low", 1),
        ("q=100%25", 1),
        ("q=_", 0),
        (f"assignee_id={actors['member']['id']}", 1),
    ):
        result = await client.get(path + "?" + query, headers=headers)
        assert result.status_code == 200
        assert result.json()["total"] == count
    page = (await client.get(path + "?limit=1&offset=1&sort=-priority", headers=headers)).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert page["items"][0]["priority"] == "high"
    assert (await client.get(path + "?sort=invalid", headers=headers)).status_code == 422
    assert (await client.get(path + "?limit=101", headers=headers)).status_code == 422
    stats = (
        await client.get(f"/api/v1/workspaces/{actors['workspace']['id']}/stats", headers=headers)
    ).json()
    assert stats["total"] == 3 and stats["overdue"] == 1
    assert stats["by_status"]["done"] == 1
