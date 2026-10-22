import hashlib

from fastapi import HTTPException
from pwdlib.exceptions import UnknownHashError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.core.security import DUMMY_HASH, create_token, password_hasher
from app.models import User
from app.schemas import Login, Register


async def register(db: AsyncSession, data: Register):
    email = str(data.email).lower()
    if await db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "Email is already registered")
    user = User(
        email=email,
        full_name=data.full_name,
        password_hash=await run_in_threadpool(password_hasher.hash, data.password),
    )
    db.add(user)
    await db.flush()
    return user


async def login(db: AsyncSession, data: Login):
    user = await db.scalar(select(User).where(User.email == str(data.email).lower()))
    try:
        valid = await run_in_threadpool(
            password_hasher.verify, data.password, user.password_hash if user else DUMMY_HASH
        )
    except UnknownHashError:
        valid = False
    if not valid or user is None or not user.is_active:
        raise HTTPException(
            401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"}
        )
    return {"access_token": create_token(user.id), "token_type": "bearer"}


async def rate_limit_login(ip: str):
    settings = get_settings()
    key = "taskflow:login:" + hashlib.sha256(ip.encode()).hexdigest()
    try:
        async with Redis.from_url(settings.redis_url) as redis:
            # Atomic increment + TTL; limits shared across API replicas.
            count = await redis.eval(
                "local n=redis.call('INCR',KEYS[1]); "
                "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; return n",
                1,
                key,
                settings.login_window_seconds,
            )
    except RedisError as exc:
        raise HTTPException(503, "Login temporarily unavailable") from exc
    if count > settings.login_limit:
        raise HTTPException(
            429,
            "Too many login attempts",
            headers={"Retry-After": str(settings.login_window_seconds)},
        )
