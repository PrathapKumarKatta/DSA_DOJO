from typing import List, Tuple, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.code_chunk import CodeChunk
from app.models.source_file import SourceFile
from app.rag.embeddings import EmbeddingProvider, get_embedding_provider


class VectorStore:
    def __init__(self, db: Session, embedding_provider: Optional[EmbeddingProvider] = None):
        self.db = db
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def search_vector(
        self,
        project_id: uuid.UUID,
        query: str,
        limit: int = 20,
    ) -> List[Tuple[CodeChunk, SourceFile, float]]:
        """
        Cosine similarity search with pgvector filtered strictly by project_id.
        Returns tuples of (CodeChunk, SourceFile, similarity_score).
        """
        query_vector = self.embedding_provider.embed_query(query)

        # Distance <=> is cosine distance (0 is identical, 2 is opposite)
        # Similarity score = 1.0 - (distance / 2.0) or 1.0 - distance
        results = (
            self.db.query(
                CodeChunk,
                SourceFile,
                (1.0 - CodeChunk.embedding.cosine_distance(query_vector)).label("similarity"),
            )
            .join(SourceFile, CodeChunk.source_file_id == SourceFile.id)
            .filter(CodeChunk.project_id == project_id)
            .filter(CodeChunk.embedding.isnot(None))
            .order_by(CodeChunk.embedding.cosine_distance(query_vector).asc())
            .limit(limit)
            .all()
        )

        return [(chunk, file, float(sim)) for chunk, file, sim in results]

    def search_keyword(
        self,
        project_id: uuid.UUID,
        query: str,
        limit: int = 20,
    ) -> List[Tuple[CodeChunk, SourceFile, float]]:
        """
        PostgreSQL Full-Text Search using plainto_tsquery and ts_rank_cd.
        """
        # Clean query for tsquery
        clean_query = query.strip()
        if not clean_query:
            return []

        tsquery = func.plainto_tsquery("english", clean_query)
        rank = func.ts_rank_cd(CodeChunk.search_vector, tsquery).label("rank")

        results = (
            self.db.query(CodeChunk, SourceFile, rank)
            .join(SourceFile, CodeChunk.source_file_id == SourceFile.id)
            .filter(CodeChunk.project_id == project_id)
            .filter(CodeChunk.search_vector.op("@@")(tsquery))
            .order_by(rank.desc())
            .limit(limit)
            .all()
        )

        return [(chunk, file, float(r)) for chunk, file, r in results]
