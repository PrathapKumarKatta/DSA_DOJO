import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.project_service import ProjectService
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectListResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    req: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    return service.create_project(user_id=current_user.id, req=req)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List all user projects",
)
def list_projects(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    service = ProjectService(db)
    return service.list_projects(user_id=current_user.id, skip=skip, limit=limit)


@router.get(
    "/{id}",
    response_model=ProjectResponse,
    summary="Get project details by ID",
)
def get_project(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    service = ProjectService(db)
    return service.get_project(project_id=id, user_id=current_user.id)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
def delete_project(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service = ProjectService(db)
    service.delete_project(project_id=id, user_id=current_user.id)
