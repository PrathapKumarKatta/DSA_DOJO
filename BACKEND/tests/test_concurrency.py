import asyncio
from uuid import UUID

from app.models import User
from app.services import tasks
from app.services.permissions import lock_workspace


async def test_member_removed_while_waiting_for_write_is_denied(
    client, actors, task, factory, monkeypatch
):
    reached_lock = asyncio.Event()
    real_lock = tasks.lock_workspace

    async def observed_lock(db, workspace_id):
        reached_lock.set()
        await real_lock(db, workspace_id)

    monkeypatch.setattr(tasks, "lock_workspace", observed_lock)
    async with factory() as db, db.begin():
        wid = UUID(actors["workspace"]["id"])
        await lock_workspace(db, wid)
        pending = asyncio.create_task(
            client.patch(
                f"/api/v1/tasks/{task['id']}",
                json={"expected_version": 1, "title": "Revoked write"},
                headers=actors["member"]["headers"],
            )
        )
        await asyncio.wait_for(reached_lock.wait(), timeout=5)
        owner = await db.get(User, UUID(actors["owner"]["id"]))
        await tasks.remove_member(db, wid, UUID(actors["member"]["id"]), owner)
    response = await asyncio.wait_for(pending, timeout=5)
    assert response.status_code == 404
    saved = (
        await client.get(f"/api/v1/tasks/{task['id']}", headers=actors["owner"]["headers"])
    ).json()
    assert saved["title"] == "Build API" and saved["version"] == 2
