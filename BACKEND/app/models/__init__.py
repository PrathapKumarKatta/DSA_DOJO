from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow():
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Role(StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"


class Status(StrEnum):
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    done = "done"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


def enum_type(cls):
    return Enum(cls, native_enum=False, create_constraint=True, name=cls.__name__.lower())


class Identity:
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(Identity, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Workspace(Identity, Base):
    __tablename__ = "workspaces"
    name: Mapped[str] = mapped_column(String(120))
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))


class Membership(Base):
    __tablename__ = "memberships"
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    role: Mapped[Role] = mapped_column(enum_type(Role), default=Role.member)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        Index("ix_memberships_user", "user_id"),
        Index(
            "uq_workspace_owner",
            "workspace_id",
            unique=True,
            postgresql_where=(role == Role.owner),
            sqlite_where=(role == Role.owner),
        ),
    )


class Project(Identity, Base):
    __tablename__ = "projects"
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    __table_args__ = (
        UniqueConstraint("id", "workspace_id"),
        Index("ix_projects_workspace", "workspace_id"),
    )


class Task(Identity, Base):
    __tablename__ = "tasks"
    project_id: Mapped[UUID] = mapped_column(Uuid)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[Status] = mapped_column(enum_type(Status), default=Status.todo)
    priority: Mapped[Priority] = mapped_column(enum_type(Priority), default=Priority.medium)
    assignee_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    creator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "workspace_id"],
            ["projects.id", "projects.workspace_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "assignee_id"],
            ["memberships.workspace_id", "memberships.user_id"],
            ondelete="NO ACTION",
        ),
        CheckConstraint("version >= 1", name="positive_version"),
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_assignee_due", "assignee_id", "due_at"),
        Index("ix_tasks_project_created", "project_id", "created_at", "id"),
    )


class Comment(Identity, Base):
    __tablename__ = "comments"
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ActivityEvent(Identity, Base):
    __tablename__ = "activity_events"
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    task_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict)
    __table_args__ = (Index("ix_events_task_created", "task_id", "created_at", "id"),)


class NotificationDelivery(Identity, Base):
    __tablename__ = "notification_deliveries"
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    kind: Mapped[str] = mapped_column(String(30), default="due_reminder")
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(100), nullable=True)
    __table_args__ = (
        UniqueConstraint(
            "task_id", "recipient_id", "kind", "scheduled_for", name="uq_notification_dedup"
        ),
        CheckConstraint(
            "status IN ('pending','queued','sent','failed','cancelled')", name="delivery_status"
        ),
        Index("ix_deliveries_dispatch", "status", "next_attempt_at"),
    )
