import uuid
from sqlalchemy import String, Integer, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.session import Base
from app.core.config import settings


class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    symbol_name: Mapped[str] = mapped_column(String(255), nullable=True)
    chunk_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="block"
    )  # function, class, module, block
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    embedding = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
    search_vector = mapped_column(TSVECTOR, nullable=True)

    source_file = relationship("SourceFile", back_populates="code_chunks")
    project = relationship("Project", back_populates="code_chunks")
    citations = relationship("MessageCitation", back_populates="chunk")

    __table_args__ = (
        Index("ix_code_chunks_project_symbol", "project_id", "symbol_name"),
        Index("ix_code_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_code_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
