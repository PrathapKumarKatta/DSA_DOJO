from pathlib import Path
import uuid
from app.core.logging import logger
from app.services.ingestion_service import IngestionService
from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.ingest_codebase", bind=True, max_retries=2)
def ingest_codebase_task(
    self,
    project_id_str: str,
    job_id_str: str,
    zip_path_str: str,
    temp_dir_str: str,
):
    logger.info(f"Celery task started for project {project_id_str}, job {job_id_str}")
    try:
        IngestionService.run_ingestion_pipeline(
            project_id=uuid.UUID(project_id_str),
            job_id=uuid.UUID(job_id_str),
            zip_path=Path(zip_path_str),
            temp_dir=Path(temp_dir_str),
        )
    except Exception as exc:
        logger.error(f"Celery task failed: {exc}. Retrying...")
        raise self.retry(exc=exc, countdown=10)
