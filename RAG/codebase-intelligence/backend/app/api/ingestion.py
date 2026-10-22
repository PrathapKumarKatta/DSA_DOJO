import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.file_repo import FileRepository
from app.repositories.job_repo import JobRepository
from app.repositories.project_repo import ProjectRepository
from app.schemas.file import FileListResponse, SourceFileDetailResponse, SourceFileResponse
from app.schemas.ingestion import IngestionJobResponse, ProjectStatusResponse
from app.services.ingestion_service import IngestionService
from app.workers.tasks import ingest_codebase_task

router = APIRouter(prefix="/projects", tags=["ingestion"])


@router.post(
    "/{id}/upload",
    response_model=IngestionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload codebase ZIP file and trigger background ingestion",
)
def upload_codebase(
    id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestionJobResponse:
    ingestion_service = IngestionService(db)
    zip_path, temp_dir, job = ingestion_service.create_upload_job(
        project_id=id, user_id=current_user.id, upload_file=file
    )

    # Dispatch to background: Try Celery first; if Redis broker is unreachable, fallback to FastAPI background task
    try:
        ingest_codebase_task.delay(
            str(id), str(job.id), str(zip_path), str(temp_dir)
        )
    except Exception:
        # Resilient fallback to FastAPI background task
        background_tasks.add_task(
            IngestionService.run_ingestion_pipeline,
            project_id=id,
            job_id=job.id,
            zip_path=zip_path,
            temp_dir=temp_dir,
        )

    return IngestionJobResponse.model_validate(job)


@router.get(
    "/{id}/status",
    response_model=ProjectStatusResponse,
    summary="Get project ingestion status and active job progress",
)
def get_project_status(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectStatusResponse:
    project_repo = ProjectRepository(db)
    job_repo = JobRepository(db)

    project = project_repo.get_by_id_and_user(id, current_user.id)
    if not project:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        )

    job = job_repo.get_latest_by_project(id)
    job_res = IngestionJobResponse.model_validate(job) if job else None

    return ProjectStatusResponse(
        project_id=project.id,
        project_status=project.status,
        active_job=job_res,
    )


@router.get(
    "/{id}/files",
    response_model=FileListResponse,
    summary="List all indexed files for a project",
)
def list_project_files(
    id: uuid.UUID,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileListResponse:
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id_and_user(id, current_user.id)
    if not project:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        )

    file_repo = FileRepository(db)
    files = file_repo.list_by_project(id, skip=skip, limit=limit)
    total = file_repo.count_by_project(id)

    return FileListResponse(
        items=[SourceFileResponse.model_validate(f) for f in files],
        total=total,
    )


@router.get(
    "/{id}/files/{file_id}",
    response_model=SourceFileDetailResponse,
    summary="Get source code content and metadata of a specific file",
)
def get_file_content(
    id: uuid.UUID,
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SourceFileDetailResponse:
    project_repo = ProjectRepository(db)
    project = project_repo.get_by_id_and_user(id, current_user.id)
    if not project:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or unauthorized.",
        )

    file_repo = FileRepository(db)
    file = file_repo.get_by_id_and_project(file_id, id)
    if not file:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source file not found.",
        )

    return SourceFileDetailResponse.model_validate(file)
