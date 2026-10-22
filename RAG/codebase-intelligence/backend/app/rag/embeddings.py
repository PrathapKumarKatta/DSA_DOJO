from abc import ABC, abstractmethod
import hashlib
from typing import List, Optional
import numpy as np
from app.core.config import settings
from app.core.logging import logger


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of document strings."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single search query."""
        pass


class SentenceTransformersEmbedding(EmbeddingProvider):
    _instance: Optional["SentenceTransformersEmbedding"] = None
    _model = None

    def __init__(self, model_name: Optional[str] = None):
        self._model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._dimension = settings.EMBEDDING_DIMENSION

    @classmethod
    def get_instance(cls, model_name: Optional[str] = None) -> "SentenceTransformersEmbedding":
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    def _ensure_model(self):
        if self._model is None:
            logger.info(f"Loading SentenceTransformers model: {self._model_name}...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            if hasattr(self._model, "get_embedding_dimension"):
                self._dimension = self._model.get_embedding_dimension()
            else:
                self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model {self._model_name} with dimension {self._dimension}")

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        if not texts:
            return []
        self._ensure_model()
        # BGE models benefit from normalized embeddings for cosine similarity
        embeddings = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        self._ensure_model()
        # For BGE, query can be encoded directly with normalization
        embedding = self._model.encode([text], normalize_embeddings=True)[0]
        return embedding.tolist()


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic mock embedding provider for tests and offline development."""

    def __init__(self, dimension: int = 384, model_name: str = "mock-embedding-384"):
        self._dimension = dimension
        self._model_name = model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    def _hash_to_vec(self, text: str) -> List[float]:
        # Hash input text deterministically into float vector
        h = hashlib.sha256(text.encode("utf-8")).digest()
        # Repeat bytes to fill dimension
        repeated = (h * (self._dimension // len(h) + 1))[: self._dimension]
        vec = np.array([float(b) / 255.0 for b in repeated], dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_to_vec(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._hash_to_vec(text)


def get_embedding_provider() -> EmbeddingProvider:
    provider_type = settings.EMBEDDING_PROVIDER.lower()
    if provider_type == "mock":
        return MockEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
    return SentenceTransformersEmbedding.get_instance()
