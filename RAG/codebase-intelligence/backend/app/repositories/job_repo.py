from datetime import datetime, timezone
from typing import Optional
import uuid
from sqlalchemy.orm import Session
from app.models.ingestion_job import IngestionJob


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, project_id: uuid.UUID, total_files: int = 0) -> IngestionJob:
        job = IngestionJob(
            project_id=project_id,
            status="pending",
            total_files=total_files,
            processed_files=0,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: uuid.UUID) -> Optional[IngestionJob]:
        return self.db.query(IngestionJob).filter(IngestionJob.id == job_id).first()

    def get_latest_by_project(self, project_id: uuid.UUID) -> Optional[IngestionJob]:
        return (
            self.db.query(IngestionJob)
            .filter(IngestionJob.project_id == project_id)
            .order_by(IngestionJob.created_at.desc())
            .first()
        )

    def set_status(
        self,
        job: IngestionJob,
        status: str,
        processed_files: Optional[int] = None,
        total_files: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> IngestionJob:
        job.status = status
        if processed_files is not None:
            job.processed_files = processed_files
        if total_files is not None:
            job.total_files = total_files
        if error_message is not None:
            job.error_message = error_message
        if status in ("completed", "failed"):
            job.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(job)
        return job
