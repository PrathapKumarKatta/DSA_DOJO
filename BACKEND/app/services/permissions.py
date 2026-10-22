from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Membership, Project, Role, Task, User, Workspace


async def workspace_access(db: AsyncSession, workspace_id: UUID, user: User) -> Membership:
    member = await db.get(Membership, (workspace_id, user.id))
    if member is None:
        raise HTTPException(404, "Workspace not found")
    return member


def require_manager(member: Membership):
    if member.role not in (Role.owner, Role.admin):
        raise HTTPException(403, "Owner or admin role required")


async def lock_workspace(db: AsyncSession, workspace_id: UUID):
    # Serialize membership mutations and task assignment against member removal.
    found = await db.scalar(
        select(Workspace.id).where(Workspace.id == workspace_id).with_for_update()
    )
    if found is None:
        raise HTTPException(404, "Workspace not found")


async def project_access(db: AsyncSession, project_id: UUID, user: User):
    row = (
        await db.execute(
            select(Project, Membership)
            .join(Membership, Membership.workspace_id == Project.workspace_id)
            .where(Project.id == project_id, Membership.user_id == user.id)
            .execution_options(populate_existing=True)
        )
    ).first()
    if row is None:
        raise HTTPException(404, "Project not found")
    return row


async def task_access(db: AsyncSession, task_id: UUID, user: User):
    row = (
        await db.execute(
            select(Task, Membership)
            .join(Membership, Membership.workspace_id == Task.workspace_id)
            .where(Task.id == task_id, Membership.user_id == user.id)
            .execution_options(populate_existing=True)
        )
    ).first()
    if row is None:
        raise HTTPException(404, "Task not found")
    return row


def require_task_editor(task: Task, member: Membership, user: User):
    if member.role == Role.member and user.id not in (task.creator_id, task.assignee_id):
        raise HTTPException(403, "Only creator, assignee, owner or admin may edit this task")


async def validate_assignee(db: AsyncSession, workspace_id: UUID, assignee_id: UUID | None):
    if assignee_id is not None and await db.get(Membership, (workspace_id, assignee_id)) is None:
        raise HTTPException(422, "Assignee must be a workspace member")
