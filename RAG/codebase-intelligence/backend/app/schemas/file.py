from datetime import datetime
from typing import List
import uuid
from pydantic import BaseModel, ConfigDict


class SourceFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    path: str
    language: str
    line_count: int
    size_bytes: int
    created_at: datetime


class SourceFileDetailResponse(SourceFileResponse):
    content: str


class FileListResponse(BaseModel):
    items: List[SourceFileResponse]
    total: int
