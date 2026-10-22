from uuid import UUID

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ActivityEvent, Membership, Task, User, utcnow
from app.schemas import TaskCreate, TaskUpdate
from app.services.permissions import (
    lock_workspace,
    project_access,
    require_task_editor,
    task_access,
    validate_assignee,
)


def record_event(db: AsyncSession, task: Task, user: User, action: str, payload: dict):
    db.add(
        ActivityEvent(
            workspace_id=task.workspace_id,
            actor_id=user.id,
            task_id=task.id,
            action=action,
            payload=jsonable_encoder(payload),
        )
    )


async def create_task(db: AsyncSession, project_id: UUID, user: User, data: TaskCreate):
    project, _ = await project_access(db, project_id, user)
    await lock_workspace(db, project.workspace_id)
    project, _ = await project_access(db, project_id, user)
    await validate_assignee(db, project.workspace_id, data.assignee_id)
    task = Task(
        **data.model_dump(),
        project_id=project.id,
        workspace_id=project.workspace_id,
        creator_id=user.id,
    )
    db.add(task)
    await db.flush()
    record_event(db, task, user, "task.created", data.model_dump())
    await db.flush()
    return task


async def update_task(db: AsyncSession, task_id: UUID, user: User, data: TaskUpdate):
    task, member = await task_access(db, task_id, user)
    await lock_workspace(db, task.workspace_id)
    # Reauthorize after waiting: another transaction may have removed this member.
    task, member = await task_access(db, task_id, user)
    require_task_editor(task, member, user)
    changes = data.model_dump(exclude_unset=True, exclude={"expected_version"})
    if "assignee_id" in changes:
        await validate_assignee(db, task.workspace_id, changes["assignee_id"])
    previous = {key: getattr(task, key) for key in changes}
    result = await db.execute(
        update(Task)
        .where(Task.id == task.id, Task.version == data.expected_version)
        .values(**changes, version=Task.version + 1, updated_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise HTTPException(409, "Task changed; fetch the latest version and retry")
    record_event(db, task, user, "task.updated", {"before": previous, "after": changes})
    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: UUID, user: User):
    task, member = await task_access(db, task_id, user)
    await lock_workspace(db, task.workspace_id)
    task, member = await task_access(db, task_id, user)
    # Members may delete only tasks they created; assignees may edit but not delete.
    if member.role.value == "member" and task.creator_id != user.id:
        raise HTTPException(403, "Only creator, owner or admin may delete this task")
    record_event(db, task, user, "task.deleted", {"task_id": task.id, "title": task.title})
    await db.flush()
    await db.execute(delete(Task).where(Task.id == task.id))


async def remove_member(db: AsyncSession, workspace_id: UUID, user_id: UUID, actor: User):
    # Clear assignments atomically before the composite membership FK is removed.
    tasks = (
        await db.scalars(
            select(Task).where(Task.workspace_id == workspace_id, Task.assignee_id == user_id)
        )
    ).all()
    for task in tasks:
        task.assignee_id = None
        task.version += 1
        task.updated_at = utcnow()
        record_event(db, task, actor, "task.unassigned", {"removed_member_id": user_id})
    await db.flush()
    await db.execute(
        delete(Membership).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    )
