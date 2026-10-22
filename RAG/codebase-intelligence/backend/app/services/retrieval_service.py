import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.rag.hybrid_search import HybridRetriever
from app.rag.reranker import CrossEncoderReranker
from app.repositories.project_repo import ProjectRepository
from app.schemas.search import SearchRequest, SearchResponse


class RetrievalService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.retriever = HybridRetriever(db)
        self.reranker = CrossEncoderReranker.get_instance()

    def search(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        req: SearchRequest,
    ) -> SearchResponse:
        # Strict tenant verification
        project = self.project_repo.get_by_id_and_user(project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )

        if project.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project is not ready for retrieval (current status: '{project.status}').",
            )

        # Retrieve top hybrid candidates
        candidate_count = max(req.top_k * 3, 20)
        candidates = self.retriever.retrieve(
            project_id=project_id,
            query=req.query,
            top_k=candidate_count,
        )

        # Optional Cross-Encoder reranking
        should_rerank = req.use_reranker or settings.RERANKING_ENABLED
        if should_rerank and candidates:
            final_results = self.reranker.rerank(
                query=req.query,
                candidates=candidates,
                top_k=req.top_k,
            )
        else:
            final_results = candidates[: req.top_k]

        if req.min_score > 0.0:
            final_results = [r for r in final_results if r.score >= req.min_score]

        return SearchResponse(
            query=req.query,
            total=len(final_results),
            results=final_results,
        )
