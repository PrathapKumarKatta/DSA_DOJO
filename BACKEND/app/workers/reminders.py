import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.services.notifications import deliver_reminder, schedule_reminders
from app.workers.celery_app import celery_app


async def run_with_database(operation, *args):
    # Each Celery invocation has its own event loop. Never reuse asyncpg pooled
    # connections created on a previous asyncio.run() loop.
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    try:
        return await operation(async_sessionmaker(engine, expire_on_commit=False), *args)
    finally:
        await engine.dispose()


@celery_app.task(name="reminders.scan")
def scan():
    ids = asyncio.run(run_with_database(schedule_reminders))
    for delivery_id in ids:
        deliver.delay(delivery_id)
    return len(ids)


@celery_app.task(bind=True, name="reminders.deliver", max_retries=5)
def deliver(self, delivery_id: str):
    delay = asyncio.run(run_with_database(deliver_reminder, UUID(delivery_id)))
    if delay is not None:
        raise self.retry(countdown=delay)
