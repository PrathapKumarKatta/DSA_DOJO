from datetime import datetime
from typing import List
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    status: str
    file_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
