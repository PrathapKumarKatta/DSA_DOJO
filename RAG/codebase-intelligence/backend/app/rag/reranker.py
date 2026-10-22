import time
from typing import List, Optional
from app.core.config import settings
from app.core.logging import logger
from app.schemas.search import SearchResultChunk


class CrossEncoderReranker:
    _instance: Optional["CrossEncoderReranker"] = None
    _model = None

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.RERANKER_MODEL_NAME

    @classmethod
    def get_instance(cls, model_name: Optional[str] = None) -> "CrossEncoderReranker":
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    def _ensure_model(self):
        if self._model is None:
            logger.info(f"Loading CrossEncoder reranker model: {self.model_name}...")
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
                logger.info(f"CrossEncoder model {self.model_name} loaded successfully.")
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder model {self.model_name}: {e}")
                self._model = False

    def rerank(
        self,
        query: str,
        candidates: List[SearchResultChunk],
        top_k: int = 5,
    ) -> List[SearchResultChunk]:
        """
        Rerank a bounded candidate set using cross-encoder.
        Records execution latency. Gracefully falls back if model is unavailable.
        """
        if not candidates or len(candidates) <= 1:
            return candidates[:top_k]

        start_time = time.perf_counter()
        self._ensure_model()

        if self._model is False or self._model is None:
            logger.debug("CrossEncoder not available; returning original ranking.")
            return candidates[:top_k]

        try:
            pairs = [[query, f"File: {c.file_path}\n{c.content}"] for c in candidates]
            scores = self._model.predict(pairs)

            # Pair candidates with new cross-encoder scores
            scored_candidates = []
            for candidate, score in zip(candidates, scores):
                candidate_copy = candidate.model_copy()
                candidate_copy.score = float(score)
                candidate_copy.retrieval_method = "reranked"
                scored_candidates.append(candidate_copy)

            # Sort descending by cross-encoder score
            scored_candidates.sort(key=lambda x: x.score, reverse=True)
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Reranked {len(candidates)} candidates in {elapsed_ms:.2f}ms. Top score: {scored_candidates[0].score:.4f}"
            )
            return scored_candidates[:top_k]
        except Exception as e:
            logger.error(f"Error during reranking: {e}. Falling back to initial ranks.")
            return candidates[:top_k]
