from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from app.models import Priority, Role, Status


def not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Must not be blank")
    return value


Name = Annotated[str, Field(min_length=1, max_length=120), AfterValidator(not_blank)]
Title = Annotated[str, Field(min_length=1, max_length=200), AfterValidator(not_blank)]
Body = Annotated[str, Field(min_length=1, max_length=10000), AfterValidator(not_blank)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Register(Input):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: Name


class Login(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class Token(Read):
    access_token: str
    token_type: str = "bearer"


class UserRead(Read):
    id: UUID
    email: str
    full_name: str
    created_at: datetime


class ProfileUpdate(Input):
    full_name: Name


class WorkspaceCreate(Input):
    name: Name


class WorkspaceRead(Read):
    id: UUID
    name: str
    owner_id: UUID
    created_at: datetime


class MemberAdd(Input):
    user_id: UUID
    role: Role = Role.member


class MemberRole(Input):
    role: Role


class MemberRead(Read):
    workspace_id: UUID
    user_id: UUID
    role: Role
    joined_at: datetime


class ProjectCreate(Input):
    name: Name
    description: str = Field(default="", max_length=10000)


class ProjectRead(Read):
    id: UUID
    workspace_id: UUID
    name: str
    description: str
    created_by: UUID
    created_at: datetime


class TaskCreate(Input):
    title: Title
    description: str = Field(default="", max_length=10000)
    status: Status = Status.todo
    priority: Priority = Priority.medium
    assignee_id: UUID | None = None
    due_at: AwareDatetime | None = None


class TaskUpdate(Input):
    expected_version: int = Field(ge=1)
    title: Title | None = None
    description: str | None = Field(default=None, max_length=10000)
    status: Status | None = None
    priority: Priority | None = None
    assignee_id: UUID | None = None
    due_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def check_fields(self):
        fields = self.model_fields_set - {"expected_version"}
        if not fields:
            raise ValueError("Supply at least one changed field")
        for field in fields - {"assignee_id", "due_at"}:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class TaskRead(Read):
    id: UUID
    project_id: UUID
    workspace_id: UUID
    title: str
    description: str
    status: Status
    priority: Priority
    assignee_id: UUID | None
    creator_id: UUID
    due_at: datetime | None
    version: int
    created_at: datetime
    updated_at: datetime


class CommentCreate(Input):
    body: Body


class CommentRead(Read):
    id: UUID
    task_id: UUID
    author_id: UUID
    body: str
    created_at: datetime
    edited_at: datetime | None


class ActivityRead(Read):
    id: UUID
    workspace_id: UUID
    actor_id: UUID
    task_id: UUID | None
    action: str
    payload: dict
    created_at: datetime


class Page[T](Read):
    items: list[T]
    total: int
    limit: int
    offset: int


class Stats(Read):
    total: int
    overdue: int
    by_status: dict[str, int]
