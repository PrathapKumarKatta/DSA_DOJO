from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    processed_files: int
    total_files: int
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ProjectStatusResponse(BaseModel):
    project_id: uuid.UUID
    project_status: str
    active_job: Optional[IngestionJobResponse] = None
