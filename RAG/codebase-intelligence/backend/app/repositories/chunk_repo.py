from typing import List, Optional
import uuid
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.code_chunk import CodeChunk


class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, chunk_id: uuid.UUID) -> Optional[CodeChunk]:
        return self.db.query(CodeChunk).filter(CodeChunk.id == chunk_id).first()

    def get_by_id_and_project(
        self, chunk_id: uuid.UUID, project_id: uuid.UUID
    ) -> Optional[CodeChunk]:
        return (
            self.db.query(CodeChunk)
            .filter(CodeChunk.id == chunk_id, CodeChunk.project_id == project_id)
            .first()
        )

    def list_by_file(self, source_file_id: uuid.UUID) -> List[CodeChunk]:
        return (
            self.db.query(CodeChunk)
            .filter(CodeChunk.source_file_id == source_file_id)
            .order_by(CodeChunk.start_line.asc())
            .all()
        )

    def count_by_project(self, project_id: uuid.UUID) -> int:
        return (
            self.db.query(func.count(CodeChunk.id))
            .filter(CodeChunk.project_id == project_id)
            .scalar()
            or 0
        )

    def create(
        self,
        source_file_id: uuid.UUID,
        project_id: uuid.UUID,
        content: str,
        symbol_name: Optional[str],
        chunk_type: str,
        start_line: int,
        end_line: int,
        content_hash: str,
        embedding: Optional[List[float]] = None,
    ) -> CodeChunk:
        chunk = CodeChunk(
            source_file_id=source_file_id,
            project_id=project_id,
            content=content,
            symbol_name=symbol_name,
            chunk_type=chunk_type,
            start_line=start_line,
            end_line=end_line,
            content_hash=content_hash,
            embedding=embedding,
        )
        self.db.add(chunk)
        self.db.flush()
        return chunk

    def bulk_add(self, chunks: List[CodeChunk]) -> None:
        self.db.add_all(chunks)
        self.db.flush()

    def delete_by_project(self, project_id: uuid.UUID) -> None:
        self.db.query(CodeChunk).filter(CodeChunk.project_id == project_id).delete()
        self.db.commit()
