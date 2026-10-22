from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query, Response
from sqlalchemy import case, func, or_, select

from app.api.dependencies import DB, CurrentUser
from app.models import ActivityEvent, Comment, Priority, Status, Task
from app.schemas import (
    ActivityRead,
    CommentCreate,
    CommentRead,
    Page,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)
from app.services import tasks
from app.services.permissions import lock_workspace, project_access, task_access

router = APIRouter(tags=["Tasks"])


@router.post("/projects/{project_id}/tasks", response_model=TaskRead, status_code=201)
async def create(project_id: UUID, data: TaskCreate, db: DB, user: CurrentUser):
    return await tasks.create_task(db, project_id, user, data)


@router.get("/projects/{project_id}/tasks", response_model=Page[TaskRead])
async def listing(
    project_id: UUID,
    db: DB,
    user: CurrentUser,
    status: Status | None = None,
    priority: Priority | None = None,
    assignee_id: UUID | None = None,
    q: str | None = Query(None, max_length=200),
    sort: Literal[
        "created_at", "-created_at", "due_at", "-due_at", "priority", "-priority"
    ] = "-created_at",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    await project_access(db, project_id, user)
    query = select(Task).where(Task.project_id == project_id)
    for column, value in (
        (Task.status, status),
        (Task.priority, priority),
        (Task.assignee_id, assignee_id),
    ):
        if value is not None:
            query = query.where(column == value)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                Task.title.ilike(f"%{escaped}%", escape="\\"),
                Task.description.ilike(f"%{escaped}%", escape="\\"),
            )
        )
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    column = {
        "created_at": Task.created_at,
        "due_at": Task.due_at,
        "priority": case(
            (Task.priority == Priority.low, 1),
            (Task.priority == Priority.medium, 2),
            (Task.priority == Priority.high, 3),
            else_=4,
        ),
    }[sort.lstrip("-")]
    order = column.desc() if sort.startswith("-") else column.asc()
    items = (
        await db.scalars(
            query.order_by(order.nulls_last(), Task.id.desc()).limit(limit).offset(offset)
        )
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/tasks/{task_id}", response_model=TaskRead)
async def read(task_id: UUID, db: DB, user: CurrentUser):
    task, _ = await task_access(db, task_id, user)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskRead)
async def update(task_id: UUID, data: TaskUpdate, db: DB, user: CurrentUser):
    return await tasks.update_task(db, task_id, user, data)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete(task_id: UUID, db: DB, user: CurrentUser):
    await tasks.delete_task(db, task_id, user)
    return Response(status_code=204)


@router.post(
    "/tasks/{task_id}/comments", response_model=CommentRead, status_code=201, tags=["Comments"]
)
async def add_comment(task_id: UUID, data: CommentCreate, db: DB, user: CurrentUser):
    task, _ = await task_access(db, task_id, user)
    await lock_workspace(db, task.workspace_id)
    task, _ = await task_access(db, task_id, user)
    comment = Comment(task_id=task_id, author_id=user.id, body=data.body)
    db.add(comment)
    await db.flush()
    tasks.record_event(db, task, user, "comment.created", {"comment_id": comment.id})
    return comment


@router.get("/tasks/{task_id}/comments", response_model=Page[CommentRead], tags=["Comments"])
async def comments(
    task_id: UUID,
    db: DB,
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    await task_access(db, task_id, user)
    query = select(Comment).where(Comment.task_id == task_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (
        await db.scalars(query.order_by(Comment.created_at, Comment.id).limit(limit).offset(offset))
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/tasks/{task_id}/activity", response_model=Page[ActivityRead], tags=["Activity"])
async def activity(
    task_id: UUID,
    db: DB,
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    await task_access(db, task_id, user)
    query = select(ActivityEvent).where(ActivityEvent.task_id == task_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (
        await db.scalars(
            query.order_by(ActivityEvent.created_at.desc(), ActivityEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}
