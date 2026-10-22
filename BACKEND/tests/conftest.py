import os
import subprocess
import sys
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Only the explicitly named test database can be touched by this suite.
TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://taskflow:dev_password_only@127.0.0.1:5432/taskflow_test",
)
url = make_url(TEST_URL)
if url.get_backend_name() != "postgresql" or not (url.database or "").endswith("_test"):
    raise RuntimeError("TEST_DATABASE_URL must be PostgreSQL with a database name ending in _test")
os.environ["DATABASE_URL"] = TEST_URL
os.environ["JWT_SECRET"] = "test-only-secret-with-sufficient-length-1234567890"
os.environ["ENVIRONMENT"] = "test"
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://127.0.0.1:6379/15")

from app.core.config import get_settings  # noqa: E402
from app.core.security import create_token  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402
from app.services import auth  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)


@pytest.fixture
async def factory(migrated_database):
    engine = create_async_engine(TEST_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        await connection.execute(text(f"TRUNCATE TABLE {names} CASCADE"))
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def client(factory, monkeypatch):
    get_settings.cache_clear()
    app = create_app()

    async def test_db():
        async with factory() as db:
            try:
                yield db
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def no_rate_limit(ip):
        pass

    monkeypatch.setattr(auth, "rate_limit_login", no_rate_limit)
    app.dependency_overrides[get_db] = test_db
    transport = ASGITransport(app=app, client=(str(uuid4()), 123))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def actors(client):
    users = {}
    for role in ("owner", "admin", "member", "other", "outsider"):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"{role}@example.com",
                "password": "correct-horse-123",
                "full_name": role,
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        from uuid import UUID

        users[role] = {
            **data,
            "headers": {"Authorization": f"Bearer {create_token(UUID(data['id']))}"},
        }
    response = await client.post(
        "/api/v1/workspaces", json={"name": "Engineering"}, headers=users["owner"]["headers"]
    )
    assert response.status_code == 201, response.text
    workspace = response.json()
    for role in ("admin", "member", "other"):
        response = await client.post(
            f"/api/v1/workspaces/{workspace['id']}/members",
            json={
                "user_id": users[role]["id"],
                "role": "admin" if role == "admin" else "member",
            },
            headers=users["owner"]["headers"],
        )
        assert response.status_code == 201, response.text
    response = await client.post(
        f"/api/v1/workspaces/{workspace['id']}/projects",
        json={"name": "Launch"},
        headers=users["owner"]["headers"],
    )
    assert response.status_code == 201, response.text
    users["workspace"] = workspace
    users["project"] = response.json()
    return users


@pytest.fixture
async def task(client, actors):
    response = await client.post(
        f"/api/v1/projects/{actors['project']['id']}/tasks",
        json={
            "title": "Build API",
            "assignee_id": actors["member"]["id"],
            "priority": "high",
        },
        headers=actors["owner"]["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()
