from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("dummy-password-to-equalize-failed-login-timing")


def create_token(user_id: UUID) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
            "iss": "taskflow",
            "aud": "taskflow-api",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_token(token: str) -> UUID:
    try:
        claims = jwt.decode(
            token,
            get_settings().jwt_secret,
            algorithms=["HS256"],
            audience="taskflow-api",
            issuer="taskflow",
            options={"require": ["sub", "exp", "iat"]},
        )
        return UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise HTTPException(
            401, "Invalid or expired token", headers={"WWW-Authenticate": "Bearer"}
        ) from exc
