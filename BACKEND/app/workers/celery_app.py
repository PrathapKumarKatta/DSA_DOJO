from celery import Celery

from app.core.config import get_settings

celery_app = Celery("taskflow", broker=get_settings().redis_url, include=["app.workers.reminders"])
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    beat_schedule={"scan-reminders": {"task": "reminders.scan", "schedule": 60.0}},
)
