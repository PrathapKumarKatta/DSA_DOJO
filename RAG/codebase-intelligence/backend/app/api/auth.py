from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    req: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    auth_service = AuthService(db)
    return auth_service.register(req)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login with JWT generation",
)
def login(
    req: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    auth_service = AuthService(db)
    return auth_service.login(req)


@router.post(
    "/token",
    response_model=TokenResponse,
    include_in_schema=False,
)
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    auth_service = AuthService(db)
    req = UserLoginRequest(email=form_data.username, password=form_data.password)
    return auth_service.login(req)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
