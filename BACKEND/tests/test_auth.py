from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.security import create_token
from app.models import User


async def test_register_login_profile(client, factory):
    data = {"email": "Alice@Example.com", "password": "very-good-password", "full_name": "Alice"}
    result = await client.post("/api/v1/auth/register", json=data)
    assert result.status_code == 201
    assert result.json()["email"] == "alice@example.com"
    assert "password_hash" not in result.json()
    async with factory() as db:
        user = await db.get(User, UUID(result.json()["id"]))
        assert user.password_hash.startswith("$argon2id$")
    assert (await client.post("/api/v1/auth/register", json=data)).status_code == 409
    token = await client.post(
        "/api/v1/auth/login", json={"email": data["email"], "password": data["password"]}
    )
    assert token.status_code == 200
    headers = {"Authorization": "Bearer " + token.json()["access_token"]}
    assert (await client.get("/api/v1/users/me", headers=headers)).json()["full_name"] == "Alice"
    update = await client.patch(
        "/api/v1/users/me", json={"full_name": "Alice Smith"}, headers=headers
    )
    assert update.json()["full_name"] == "Alice Smith"


async def test_wrong_password_and_unknown_email_are_generic(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing@example.com",
            "password": "correct-password",
            "full_name": "Existing",
        },
    )
    for email in ("missing@example.com", "existing@example.com"):
        result = await client.post("/api/v1/auth/login", json={"email": email, "password": "bad"})
        assert result.status_code == 401
        assert result.json()["detail"] == "Invalid email or password"


@pytest.mark.parametrize("token", [None, "invalid", "", create_token(uuid4())])
async def test_missing_invalid_and_nonexistent_user_token(client, token):
    headers = {"Authorization": f"Bearer {token}"} if token is not None else {}
    assert (await client.get("/api/v1/users/me", headers=headers)).status_code == 401


async def test_expired_token_and_disabled_user(client, actors, factory):
    now = datetime.now(UTC)
    claims = {
        "sub": actors["owner"]["id"],
        "exp": now - timedelta(minutes=1),
        "iat": now - timedelta(hours=1),
        "iss": "taskflow",
        "aud": "taskflow-api",
    }
    token = jwt.encode(claims, get_settings().jwt_secret, algorithm="HS256")
    assert (
        await client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    ).status_code == 401
    async with factory() as db, db.begin():
        user = await db.get(User, UUID(actors["owner"]["id"]))
        user.is_active = False
    assert (
        await client.get("/api/v1/users/me", headers=actors["owner"]["headers"])
    ).status_code == 401


@pytest.mark.parametrize(
    "patch", [{"email": "bad"}, {"password": "short"}, {"full_name": "  "}, {"role": "owner"}]
)
async def test_registration_validation(client, patch):
    data = {"email": "valid@example.com", "password": "long-enough-password", "full_name": "Valid"}
    assert (await client.post("/api/v1/auth/register", json=data | patch)).status_code == 422


def test_configuration_requires_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret="short")
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            jwt_secret="replace_with_a_random_secret_at_least_32_characters",
            environment="production",
        )


async def test_health_and_openapi(client):
    assert (await client.get("/health")).json() == {"status": "ok"}
    assert (await client.get("/health/ready")).status_code == 200
    assert (await client.get("/docs")).status_code == 200
    spec = (await client.get("/openapi.json")).json()
    assert "/api/v1/tasks/{task_id}" in spec["paths"]
    assert spec["components"]["schemas"]["TaskUpdate"]["required"] == ["expected_version"]
