import hashlib
import shutil
from pathlib import Path
from typing import List
import uuid
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.config import settings
from app.core.logging import logger
from app.db.session import SessionLocal
from app.models.code_chunk import CodeChunk
from app.models.ingestion_job import IngestionJob
from app.models.project import Project
from app.rag.chunker import chunk_file
from app.rag.embeddings import get_embedding_provider
from app.rag.file_discovery import extract_and_discover_files
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.file_repo import FileRepository
from app.repositories.job_repo import JobRepository
from app.repositories.project_repo import ProjectRepository


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.job_repo = JobRepository(db)
        self.file_repo = FileRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.embedding_provider = get_embedding_provider()

    def create_upload_job(
        self,
        project_id: uuid.UUID,
        user_id: uuid.UUID,
        upload_file: UploadFile,
    ) -> tuple[Path, Path, IngestionJob]:
        # Validate project ownership
        project = self.project_repo.get_by_id_and_user(project_id, user_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found or you do not have permission to access it.",
            )

        if not upload_file.filename.lower().endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .zip archive uploads are supported.",
            )

        # Save to temporary storage
        upload_id = uuid.uuid4().hex[:8]
        temp_dir = settings.storage_path / f"temp_{project_id}_{upload_id}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        zip_path = temp_dir / "upload.zip"

        try:
            with open(zip_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to store upload archive: {e}",
            )

        file_size_mb = zip_path.stat().st_size / (1024 * 1024)
        if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Upload size ({file_size_mb:.1f}MB) exceeds limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )

        # Update project status and create IngestionJob
        self.project_repo.update_status(project, "processing")
        job = self.job_repo.create(project_id=project_id, total_files=0)

        return zip_path, temp_dir, job

    @staticmethod
    def run_ingestion_pipeline(
        project_id: uuid.UUID,
        job_id: uuid.UUID,
        zip_path: Path,
        temp_dir: Path,
    ) -> None:
        """
        Idempotent background pipeline execution for codebase indexing.
        Can be invoked from Celery or directly from FastAPI BackgroundTasks.
        """
        db = SessionLocal()
        try:
            job_repo = JobRepository(db)
            project_repo = ProjectRepository(db)
            file_repo = FileRepository(db)
            chunk_repo = ChunkRepository(db)
            embedding_provider = get_embedding_provider()

            job = job_repo.get_by_id(job_id)
            project = db.query(Project).filter(Project.id == project_id).first()
            if not job or not project:
                logger.error(f"Cannot run ingestion: missing project {project_id} or job {job_id}")
                return

            job_repo.set_status(job, "processing")
            extract_dir = temp_dir / "extracted"

            logger.info(f"Extracting and discovering files for project {project_id}...")
            discovered_files = extract_and_discover_files(zip_path, extract_dir)
            total_files = len(discovered_files)
            job_repo.set_status(job, "processing", processed_files=0, total_files=total_files)

            # Idempotency: Clean previous files and chunks for this project
            chunk_repo.delete_by_project(project_id)
            file_repo.delete_by_project(project_id)

            # Process files and generate chunks
            all_chunks_to_insert: List[CodeChunk] = []
            chunk_texts: List[str] = []

            for idx, df in enumerate(discovered_files, start=1):
                content_hash = hashlib.sha256(df.content.encode("utf-8")).hexdigest()
                source_file = file_repo.create(
                    project_id=project_id,
                    path=df.relative_path,
                    language=df.language,
                    content_hash=content_hash,
                    line_count=df.line_count,
                    size_bytes=df.size_bytes,
                    content=df.content,
                )

                file_chunks = chunk_file(
                    file_path=df.relative_path,
                    language=df.language,
                    content=df.content,
                )

                for fc in file_chunks:
                    chunk = CodeChunk(
                        source_file_id=source_file.id,
                        project_id=project_id,
                        content=fc.content,
                        symbol_name=fc.symbol_name,
                        chunk_type=fc.chunk_type,
                        start_line=fc.start_line,
                        end_line=fc.end_line,
                        content_hash=fc.content_hash,
                        # Populate search_vector using postgres full text parser
                        search_vector=func.to_tsvector("english", fc.content),
                    )
                    all_chunks_to_insert.append(chunk)
                    chunk_texts.append(fc.content)

                if idx % 20 == 0 or idx == total_files:
                    job_repo.set_status(job, "processing", processed_files=idx)

            # Generate batch embeddings
            if chunk_texts:
                logger.info(
                    f"Generating embeddings for {len(chunk_texts)} chunks using {embedding_provider.model_name}..."
                )
                embeddings = embedding_provider.embed_documents(chunk_texts, batch_size=32)
                for chunk, emb in zip(all_chunks_to_insert, embeddings):
                    chunk.embedding = emb

            # Save chunks to PostgreSQL
            chunk_repo.bulk_add(all_chunks_to_insert)
            db.commit()

            # Mark completed
            job_repo.set_status(job, "completed", processed_files=total_files)
            project_repo.update_status(project, "ready")
            logger.info(
                f"Successfully completed ingestion for project {project_id}: "
                f"{total_files} files, {len(all_chunks_to_insert)} chunks indexed."
            )

        except Exception as e:
            logger.error(f"Ingestion failed for project {project_id}: {e}", exc_info=True)
            db.rollback()
            try:
                job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
                project = db.query(Project).filter(Project.id == project_id).first()
                if job:
                    job_repo = JobRepository(db)
                    job_repo.set_status(job, "failed", error_message=str(e))
                if project:
                    project_repo = ProjectRepository(db)
                    project_repo.update_status(project, "failed")
            except Exception as inner_e:
                logger.error(f"Failed to record job failure: {inner_e}")
        finally:
            db.close()
            # Clean up temporary extraction files
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
