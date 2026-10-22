from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[uuid.UUID] = None
    top_k: int = Field(default=5, ge=1, le=20)
    use_reranker: bool = False


class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: Optional[uuid.UUID] = None
    file_path: str
    start_line: int
    end_line: int
    snippet: Optional[str] = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: List[CitationResponse] = []
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message: MessageResponse


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    created_at: datetime
    message_count: int = 0


class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []
