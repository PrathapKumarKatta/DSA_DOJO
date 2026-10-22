from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.models.code_chunk import CodeChunk
from app.models.source_file import SourceFile
from app.rag.vector_store import VectorStore
from app.schemas.search import SearchResultChunk


@dataclass
class ScoredChunk:
    chunk: CodeChunk
    file: SourceFile
    score: float
    retrieval_method: str


def reciprocal_rank_fusion(
    vector_results: List[Tuple[CodeChunk, SourceFile, float]],
    keyword_results: List[Tuple[CodeChunk, SourceFile, float]],
    k: int = 60,
    top_k: int = 5,
) -> List[SearchResultChunk]:
    """
    Combine vector and keyword results using Reciprocal Rank Fusion (RRF).
    RRF Score = 1 / (k + rank_vector) + 1 / (k + rank_keyword)
    """
    scores: Dict[uuid.UUID, float] = {}
    methods: Dict[uuid.UUID, str] = {}
    chunk_map: Dict[uuid.UUID, Tuple[CodeChunk, SourceFile]] = {}

    # Process vector rankings (rank starts at 1)
    for rank, (chunk, file, sim_score) in enumerate(vector_results, start=1):
        chunk_id = chunk.id
        chunk_map[chunk_id] = (chunk, file)
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))
        methods[chunk_id] = "vector"

    # Process keyword rankings (rank starts at 1)
    for rank, (chunk, file, kw_score) in enumerate(keyword_results, start=1):
        chunk_id = chunk.id
        chunk_map[chunk_id] = (chunk, file)
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + rank))
        if chunk_id in methods and methods[chunk_id] == "vector":
            methods[chunk_id] = "hybrid"
        else:
            methods[chunk_id] = "keyword"

    # Sort descending by fused score
    sorted_items = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    results: List[SearchResultChunk] = []
    for chunk_id, score in sorted_items[:top_k]:
        chunk, file = chunk_map[chunk_id]
        results.append(
            SearchResultChunk(
                chunk_id=chunk.id,
                source_file_id=file.id,
                file_path=file.path,
                symbol_name=chunk.symbol_name,
                chunk_type=chunk.chunk_type,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                content=chunk.content,
                score=round(score, 6),
                retrieval_method=methods[chunk_id],
            )
        )

    return results


class HybridRetriever:
    def __init__(self, db: Session, vector_store: Optional[VectorStore] = None):
        self.db = db
        self.vector_store = vector_store or VectorStore(db)

    def retrieve(
        self,
        project_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        vector_candidates: int = 20,
        keyword_candidates: int = 20,
    ) -> List[SearchResultChunk]:
        """Execute hybrid search on vector similarity and keyword full-text matching."""
        vector_hits = self.vector_store.search_vector(
            project_id=project_id, query=query, limit=vector_candidates
        )
        keyword_hits = self.vector_store.search_keyword(
            project_id=project_id, query=query, limit=keyword_candidates
        )

        return reciprocal_rank_fusion(
            vector_results=vector_hits,
            keyword_results=keyword_hits,
            top_k=top_k,
        )
