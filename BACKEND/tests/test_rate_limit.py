import pytest
from fastapi import HTTPException
from redis.asyncio import Redis

from app.core.config import get_settings
from app.services.auth import rate_limit_login


async def test_shared_redis_login_limit():
    from uuid import uuid4

    ip = str(uuid4())
    for _ in range(get_settings().login_limit):
        await rate_limit_login(ip)
    with pytest.raises(HTTPException) as exc:
        await rate_limit_login(ip)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


async def test_rate_limit_fails_closed_when_redis_unavailable(monkeypatch):
    from redis.exceptions import ConnectionError

    async def unavailable(*args, **kwargs):
        raise ConnectionError("unavailable")

    monkeypatch.setattr(Redis, "eval", unavailable)
    with pytest.raises(HTTPException) as exc:
        await rate_limit_login("test-redis-unavailable")
    assert exc.value.status_code == 503
