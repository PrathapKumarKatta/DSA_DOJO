from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import func, select

from app.api.dependencies import DB, CurrentUser
from app.models import ActivityEvent, Membership, Role, Status, Task, User, Workspace, utcnow
from app.schemas import (
    ActivityRead,
    MemberAdd,
    MemberRead,
    MemberRole,
    Page,
    Stats,
    WorkspaceCreate,
    WorkspaceRead,
)
from app.services.permissions import lock_workspace, require_manager, workspace_access
from app.services.tasks import remove_member

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=201)
async def create(data: WorkspaceCreate, db: DB, user: CurrentUser):
    workspace = Workspace(name=data.name, owner_id=user.id)
    db.add(workspace)
    await db.flush()
    db.add(Membership(workspace_id=workspace.id, user_id=user.id, role=Role.owner))
    await db.flush()
    return workspace


@router.get("", response_model=Page[WorkspaceRead])
async def listing(
    db: DB, user: CurrentUser, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)
):
    query = select(Workspace).join(Membership).where(Membership.user_id == user.id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (
        await db.scalars(
            query.order_by(Workspace.created_at.desc(), Workspace.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def read(workspace_id: UUID, db: DB, user: CurrentUser):
    await workspace_access(db, workspace_id, user)
    return await db.get(Workspace, workspace_id)


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(workspace_id: UUID, db: DB, user: CurrentUser):
    await lock_workspace(db, workspace_id)
    member = await workspace_access(db, workspace_id, user)
    if member.role != Role.owner:
        raise HTTPException(403, "Only the owner may delete the workspace")
    await db.delete(await db.get(Workspace, workspace_id))
    return Response(status_code=204)


@router.get("/{workspace_id}/members", response_model=list[MemberRead])
async def members(workspace_id: UUID, db: DB, user: CurrentUser):
    await workspace_access(db, workspace_id, user)
    return (
        await db.scalars(
            select(Membership)
            .where(Membership.workspace_id == workspace_id)
            .order_by(Membership.joined_at, Membership.user_id)
        )
    ).all()


@router.post("/{workspace_id}/members", response_model=MemberRead, status_code=201)
async def add_member(workspace_id: UUID, data: MemberAdd, db: DB, user: CurrentUser):
    await lock_workspace(db, workspace_id)
    actor = await workspace_access(db, workspace_id, user)
    require_manager(actor)
    if data.role == Role.owner or (actor.role == Role.admin and data.role != Role.member):
        raise HTTPException(403, "Only owner may grant admin; ownership cannot be assigned")
    target = await db.get(User, data.user_id)
    if target is None or not target.is_active:
        raise HTTPException(404, "User not found")
    member = Membership(workspace_id=workspace_id, user_id=data.user_id, role=data.role)
    db.add(member)
    await db.flush()
    return member


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberRead)
async def change_role(
    workspace_id: UUID, user_id: UUID, data: MemberRole, db: DB, user: CurrentUser
):
    await lock_workspace(db, workspace_id)
    actor = await workspace_access(db, workspace_id, user)
    if actor.role != Role.owner or data.role == Role.owner:
        raise HTTPException(403, "Only owner may change roles; ownership is fixed in v1")
    target = await db.get(Membership, (workspace_id, user_id))
    if target is None:
        raise HTTPException(404, "Member not found")
    if target.role == Role.owner:
        raise HTTPException(403, "Cannot demote owner")
    target.role = data.role
    await db.flush()
    return target


@router.delete("/{workspace_id}/members/{user_id}", status_code=204)
async def delete_member(workspace_id: UUID, user_id: UUID, db: DB, user: CurrentUser):
    await lock_workspace(db, workspace_id)
    actor = await workspace_access(db, workspace_id, user)
    require_manager(actor)
    target = await db.get(Membership, (workspace_id, user_id))
    if target is None:
        raise HTTPException(404, "Member not found")
    if target.role == Role.owner or (actor.role == Role.admin and target.role != Role.member):
        raise HTTPException(403, "Cannot remove this member")
    await remove_member(db, workspace_id, user_id, user)
    return Response(status_code=204)


@router.get("/{workspace_id}/stats", response_model=Stats)
async def stats(workspace_id: UUID, db: DB, user: CurrentUser):
    await workspace_access(db, workspace_id, user)
    rows = (
        await db.execute(
            select(Task.status, func.count())
            .where(Task.workspace_id == workspace_id)
            .group_by(Task.status)
        )
    ).all()
    counts = dict.fromkeys(Status, 0)
    counts.update(dict(rows))
    overdue = await db.scalar(
        select(func.count())
        .select_from(Task)
        .where(
            Task.workspace_id == workspace_id, Task.status != Status.done, Task.due_at < utcnow()
        )
    )
    return {"total": sum(counts.values()), "by_status": counts, "overdue": overdue}


@router.get("/{workspace_id}/activity", response_model=Page[ActivityRead])
async def activity(
    workspace_id: UUID,
    db: DB,
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    await workspace_access(db, workspace_id, user)
    query = select(ActivityEvent).where(ActivityEvent.workspace_id == workspace_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (
        await db.scalars(
            query.order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}
