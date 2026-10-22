import asyncio
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select

from app.models import NotificationDelivery, Task, utcnow
from app.services.notifications import deliver_reminder, schedule_reminders


async def make_due(factory, task):
    async with factory() as db, db.begin():
        item = await db.get(Task, UUID(task["id"]))
        item.due_at = utcnow() + timedelta(minutes=30)


async def test_scheduler_dedup_and_concurrent_delivery(factory, task):
    await make_due(factory, task)
    ids = await schedule_reminders(factory)
    assert len(ids) == 1
    assert await schedule_reminders(factory) == []
    sent = []

    def sender(recipient, title, key):
        sent.append(key)

    await asyncio.gather(*[deliver_reminder(factory, UUID(ids[0]), sender) for _ in range(2)])
    assert len(sent) == 1
    async with factory() as db:
        delivery = await db.get(NotificationDelivery, UUID(ids[0]))
        assert delivery.status == "sent" and delivery.attempts == 1 and delivery.sent_at
        assert await db.scalar(select(func.count()).select_from(NotificationDelivery)) == 1


async def test_transient_failure_retry_and_max_attempts(factory, task):
    await make_due(factory, task)
    key = UUID((await schedule_reminders(factory))[0])

    def broken_sender(*args):
        raise OSError("Transient provider failure")

    for attempt in range(1, 6):
        delay = await deliver_reminder(factory, key, broken_sender)
        assert delay == (30 * 2 ** (attempt - 1) if attempt < 5 else None)
        async with factory() as db, db.begin():
            delivery = await db.get(NotificationDelivery, key)
            assert delivery.attempts == attempt
            assert delivery.last_error == "OSError"
            if attempt < 5:
                delivery.next_attempt_at = utcnow() - timedelta(seconds=1)
            else:
                assert delivery.status == "failed"
    assert await deliver_reminder(factory, key, broken_sender) is None


async def test_retry_succeeds_and_expired_queue_lease_recovers(factory, task):
    await make_due(factory, task)
    key = UUID((await schedule_reminders(factory))[0])
    async with factory() as db, db.begin():
        delivery = await db.get(NotificationDelivery, key)
        delivery.next_attempt_at = utcnow() - timedelta(seconds=1)
    assert await schedule_reminders(factory) == [str(key)]

    def broken(*args):
        raise OSError()

    assert await deliver_reminder(factory, key, broken) == 30
    async with factory() as db, db.begin():
        delivery = await db.get(NotificationDelivery, key)
        delivery.next_attempt_at = utcnow() - timedelta(seconds=1)
    assert await deliver_reminder(factory, key, lambda *args: None) is None
    async with factory() as db:
        delivery = await db.get(NotificationDelivery, key)
        assert delivery.status == "sent" and delivery.attempts == 2


async def test_changed_due_date_cancels_stale_reminders(factory, task):
    await make_due(factory, task)
    key = UUID((await schedule_reminders(factory))[0])
    async with factory() as db, db.begin():
        item = await db.get(Task, UUID(task["id"]))
        item.due_at += timedelta(minutes=5)
    calls = []
    await deliver_reminder(factory, key, lambda *args: calls.append(args))
    assert not calls
    async with factory() as db:
        assert (await db.get(NotificationDelivery, key)).status == "cancelled"
    assert len(await schedule_reminders(factory)) == 1


async def test_done_tasks_cancel_queued_reminders_and_future_tasks_are_not_scheduled(factory, task):
    from app.models import Status

    async with factory() as db, db.begin():
        item = await db.get(Task, UUID(task["id"]))
        item.due_at = utcnow() + timedelta(days=5)
    assert await schedule_reminders(factory) == []
    await make_due(factory, task)
    key = UUID((await schedule_reminders(factory))[0])
    async with factory() as db, db.begin():
        item = await db.get(Task, UUID(task["id"]))
        item.status = Status.done
    sent = []
    await deliver_reminder(factory, key, lambda *args: sent.append(args))
    assert not sent
    async with factory() as db:
        assert (await db.get(NotificationDelivery, key)).status == "cancelled"
