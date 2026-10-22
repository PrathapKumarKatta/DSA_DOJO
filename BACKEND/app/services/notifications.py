import logging
import smtplib
from datetime import timedelta
from email.message import EmailMessage
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.models import NotificationDelivery, Status, Task, User, utcnow

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 5


def send_email(recipient: str, title: str, delivery_id: UUID):
    settings = get_settings()
    if settings.email_backend == "console":
        logger.warning("Development reminder delivered: delivery_id=%s", delivery_id)
        return
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = "TaskFlow task due reminder"
    # Stable Message-ID helps trace retries but SMTP does not guarantee deduplication.
    message["Message-ID"] = f"<{delivery_id}@taskflow>"
    message.set_content(f"Your task is due soon or overdue:\n\n{title}\n")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(message)


async def schedule_reminders(factory) -> list[str]:
    now = utcnow()
    async with factory() as db, db.begin():
        tasks = (
            await db.scalars(
                select(Task).where(
                    Task.due_at <= now + timedelta(hours=1),
                    Task.status != Status.done,
                )
            )
        ).all()
        for task in tasks:
            recipient = task.assignee_id or task.creator_id
            existing = await db.scalar(
                select(NotificationDelivery.id).where(
                    NotificationDelivery.task_id == task.id,
                    NotificationDelivery.recipient_id == recipient,
                    NotificationDelivery.kind == "due_reminder",
                    NotificationDelivery.scheduled_for == task.due_at,
                )
            )
            if existing:
                continue
            try:
                async with db.begin_nested():
                    db.add(
                        NotificationDelivery(
                            task_id=task.id,
                            recipient_id=recipient,
                            scheduled_for=task.due_at,
                            next_attempt_at=now,
                        )
                    )
                    await db.flush()
            except IntegrityError:
                pass  # Another scheduler inserted the same deduplication key.
        # The DB is the durable dispatch record. Expired queue leases recover broker outages.
        deliveries = (
            await db.scalars(
                select(NotificationDelivery)
                .where(
                    or_(
                        NotificationDelivery.status == "pending",
                        NotificationDelivery.status == "queued",
                    ),
                    NotificationDelivery.next_attempt_at <= now,
                )
                .order_by(NotificationDelivery.next_attempt_at)
                .limit(500)
                .with_for_update(skip_locked=True)
            )
        ).all()
        ids = []
        for delivery in deliveries:
            delivery.status = "queued"
            delivery.next_attempt_at = now + timedelta(minutes=5)
            ids.append(str(delivery.id))
        return ids


def aware(value):
    # SQLite's test driver strips tzinfo; PostgreSQL uses TIMESTAMPTZ.
    from datetime import UTC

    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


async def deliver_reminder(factory, delivery_id: UUID, sender=send_email) -> int | None:
    """Return a retry countdown after committing a failed attempt, else None."""
    import asyncio

    async with factory() as db, db.begin():
        delivery = await db.scalar(
            select(NotificationDelivery)
            .where(NotificationDelivery.id == delivery_id)
            .with_for_update()
        )
        if delivery is None or delivery.status in {"sent", "failed", "cancelled"}:
            return None
        now = utcnow()
        if delivery.status == "pending" and aware(delivery.next_attempt_at) > now:
            return max(1, int((aware(delivery.next_attempt_at) - now).total_seconds()))
        task = await db.get(Task, delivery.task_id)
        recipient = await db.get(User, delivery.recipient_id)
        if (
            task is None
            or recipient is None
            or not recipient.is_active
            or task.status == Status.done
            or task.due_at is None
            or aware(task.due_at) != aware(delivery.scheduled_for)
            or (task.assignee_id or task.creator_id) != recipient.id
        ):
            delivery.status = "cancelled"
            return None
        delivery.attempts += 1
        try:
            # Keep the event loop responsive while SMTP performs blocking network I/O.
            # Row lock prevents concurrent duplicate workers sending this delivery.
            await asyncio.to_thread(sender, recipient.email, task.title, delivery.id)
        except (OSError, smtplib.SMTPException) as exc:
            delivery.last_error = type(exc).__name__  # Never persist SMTP credentials or content.
            delay = min(30 * 2 ** (delivery.attempts - 1), 1800)
            delivery.status = "failed" if delivery.attempts >= MAX_ATTEMPTS else "pending"
            delivery.next_attempt_at = now + timedelta(seconds=delay)
            return delay if delivery.status == "pending" else None
        delivery.status = "sent"
        delivery.sent_at = utcnow()
        delivery.last_error = None
        return None
