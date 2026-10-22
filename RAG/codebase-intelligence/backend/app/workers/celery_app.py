from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "codebase_intelligence_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes max per task
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
)
