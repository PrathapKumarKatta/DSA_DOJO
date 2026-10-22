from typing import List, Optional
import uuid
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    use_reranker: bool = False
    min_score: float = 0.0


class SearchResultChunk(BaseModel):
    chunk_id: uuid.UUID
    source_file_id: uuid.UUID
    file_path: str
    symbol_name: Optional[str] = None
    chunk_type: str
    start_line: int
    end_line: int
    content: str
    score: float
    retrieval_method: str  # vector, keyword, hybrid, reranked


class SearchResponse(BaseModel):
    query: str
    total: int
    results: List[SearchResultChunk]
