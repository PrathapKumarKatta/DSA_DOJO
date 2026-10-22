from typing import List, Optional
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.source_file import SourceFile


class FileRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id_and_project(
        self, file_id: uuid.UUID, project_id: uuid.UUID
    ) -> Optional[SourceFile]:
        return (
            self.db.query(SourceFile)
            .filter(SourceFile.id == file_id, SourceFile.project_id == project_id)
            .first()
        )

    def get_by_path(
        self, project_id: uuid.UUID, path: str
    ) -> Optional[SourceFile]:
        return (
            self.db.query(SourceFile)
            .filter(SourceFile.project_id == project_id, SourceFile.path == path)
            .first()
        )

    def list_by_project(
        self, project_id: uuid.UUID, skip: int = 0, limit: int = 1000
    ) -> List[SourceFile]:
        return (
            self.db.query(SourceFile)
            .filter(SourceFile.project_id == project_id)
            .order_by(SourceFile.path.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_by_project(self, project_id: uuid.UUID) -> int:
        return (
            self.db.query(func.count(SourceFile.id))
            .filter(SourceFile.project_id == project_id)
            .scalar()
            or 0
        )

    def create(
        self,
        project_id: uuid.UUID,
        path: str,
        language: str,
        content_hash: str,
        line_count: int,
        size_bytes: int,
        content: str,
    ) -> SourceFile:
        file = SourceFile(
            project_id=project_id,
            path=path,
            language=language,
            content_hash=content_hash,
            line_count=line_count,
            size_bytes=size_bytes,
            content=content,
        )
        self.db.add(file)
        self.db.flush()
        return file

    def delete_by_project(self, project_id: uuid.UUID) -> None:
        self.db.query(SourceFile).filter(SourceFile.project_id == project_id).delete()
        self.db.commit()
