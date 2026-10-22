from typing import List, Optional, Tuple
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.project import Project
from app.models.source_file import SourceFile
from app.models.code_chunk import CodeChunk


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_and_user(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[Project]:
        return (
            self.db.query(Project)
            .filter(Project.id == project_id, Project.user_id == user_id)
            .first()
        )

    def list_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[Project]:
        return (
            self.db.query(Project)
            .filter(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_user(self, user_id: uuid.UUID) -> int:
        return (
            self.db.query(func.count(Project.id))
            .filter(Project.user_id == user_id)
            .scalar()
            or 0
        )

    def create(self, user_id: uuid.UUID, name: str) -> Project:
        project = Project(user_id=user_id, name=name, status="created")
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def update_status(self, project: Project, status: str) -> Project:
        project.status = status
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_metrics(self, project_id: uuid.UUID) -> Tuple[int, int]:
        file_count = (
            self.db.query(func.count(SourceFile.id))
            .filter(SourceFile.project_id == project_id)
            .scalar()
            or 0
        )
        chunk_count = (
            self.db.query(func.count(CodeChunk.id))
            .filter(CodeChunk.project_id == project_id)
            .scalar()
            or 0
        )
        return file_count, chunk_count

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()
