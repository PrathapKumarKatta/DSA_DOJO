from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.dependencies import DB, CurrentUser
from app.models import Project
from app.schemas import Page, ProjectCreate, ProjectRead
from app.services.permissions import lock_workspace, require_manager, workspace_access

router = APIRouter(tags=["Projects"])


@router.post("/workspaces/{workspace_id}/projects", response_model=ProjectRead, status_code=201)
async def create(workspace_id: UUID, data: ProjectCreate, db: DB, user: CurrentUser):
    await lock_workspace(db, workspace_id)
    member = await workspace_access(db, workspace_id, user)
    require_manager(member)
    project = Project(**data.model_dump(), workspace_id=workspace_id, created_by=user.id)
    db.add(project)
    await db.flush()
    return project


@router.get("/workspaces/{workspace_id}/projects", response_model=Page[ProjectRead])
async def listing(
    workspace_id: UUID,
    db: DB,
    user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    await workspace_access(db, workspace_id, user)
    query = select(Project).where(Project.workspace_id == workspace_id)
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    items = (
        await db.scalars(
            query.order_by(Project.created_at.desc(), Project.id.desc()).limit(limit).offset(offset)
        )
    ).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}
