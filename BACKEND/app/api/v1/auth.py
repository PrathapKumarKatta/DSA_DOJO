from fastapi import APIRouter, Request

from app.api.dependencies import DB, CurrentUser
from app.schemas import Login, ProfileUpdate, Register, Token, UserRead
from app.services import auth

router = APIRouter(tags=["Authentication"])


@router.post("/auth/register", response_model=UserRead, status_code=201)
async def register(data: Register, db: DB):
    return await auth.register(db, data)


@router.post("/auth/login", response_model=Token)
async def login(data: Login, request: Request, db: DB):
    await auth.rate_limit_login(request.client.host if request.client else "unknown")
    return await auth.login(db, data)


@router.get("/users/me", response_model=UserRead, tags=["Users"])
async def me(user: CurrentUser):
    return user


@router.patch("/users/me", response_model=UserRead, tags=["Users"])
async def update_me(data: ProfileUpdate, db: DB, user: CurrentUser):
    user.full_name = data.full_name
    await db.flush()
    return user
