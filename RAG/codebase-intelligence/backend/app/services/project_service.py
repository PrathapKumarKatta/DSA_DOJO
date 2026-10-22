import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.project import Project
from app.repositories.project_repo import ProjectRepository
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectListResponse,
)


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)

    def _to_response(self, project: Project) -> ProjectResponse:
        file_count, chunk_count = self.project_repo.get_metrics(project.id)
        return ProjectResponse(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            status=project.status,
            file_count=file_count,
            chunk_count=chunk_count,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )

    def create_project(
        self, user_id: uuid.UUID, req: ProjectCreateRequest
    ) -> ProjectResponse:
        project = self.project_repo.create(user_id=user_id, name=req.name.strip())
        return self._to_response(project)

    def get_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> ProjectResponse:
        project = self.project_repo.get_by_id_and_user(project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )
        return self._to_response(project)

    def list_projects(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> ProjectListResponse:
        projects = self.project_repo.list_by_user(user_id, skip=skip, limit=limit)
        total = self.project_repo.count_by_user(user_id)
        items = [self._to_response(p) for p in projects]
        return ProjectListResponse(items=items, total=total)

    def delete_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        project = self.project_repo.get_by_id_and_user(project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )
        self.project_repo.delete(project)
