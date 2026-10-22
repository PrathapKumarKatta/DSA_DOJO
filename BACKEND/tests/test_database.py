from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import ActivityEvent, Membership, Task
from app.schemas import TaskUpdate
from app.services.tasks import update_task


async def test_membership_uniqueness_and_foreign_keys(factory, actors):
    async with factory() as db:
        db.add(
            Membership(
                workspace_id=UUID(actors["workspace"]["id"]), user_id=UUID(actors["member"]["id"])
            )
        )
        with pytest.raises(IntegrityError):
            await db.commit()
        await db.rollback()
        db.add(Membership(workspace_id=uuid4(), user_id=UUID(actors["member"]["id"])))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_database_rejects_cross_workspace_assignee(factory, actors):
    async with factory() as db:
        db.add(
            Task(
                project_id=UUID(actors["project"]["id"]),
                workspace_id=UUID(actors["workspace"]["id"]),
                creator_id=UUID(actors["owner"]["id"]),
                title="Invalid assignee",
                assignee_id=UUID(actors["outsider"]["id"]),
            )
        )
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_event_and_update_rollback_together(factory, actors, task):
    from app.models import User

    async with factory() as db:
        owner = await db.get(User, UUID(actors["owner"]["id"]))
        await update_task(
            db, UUID(task["id"]), owner, TaskUpdate(expected_version=1, title="Rolled back")
        )
        await db.rollback()  # Simulates an error before transaction commit.
    async with factory() as db:
        saved = await db.get(Task, UUID(task["id"]))
        assert saved.title == "Build API" and saved.version == 1
        assert await db.scalar(select(func.count()).select_from(ActivityEvent)) == 1
