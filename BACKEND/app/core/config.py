from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://taskflow:dev_password_only@localhost:5432/taskflow"
    jwt_secret: str = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = []
    environment: Literal["development", "test", "production"] = "development"
    email_backend: Literal["console", "smtp"] = "console"
    email_from: str = "taskflow@example.com"
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_starttls: bool = True
    smtp_username: str | None = None
    smtp_password: str | None = None
    login_limit: int = Field(default=10, ge=1)
    login_window_seconds: int = Field(default=60, ge=1)

    @field_validator("database_url", mode="before")
    @classmethod
    def use_async_postgres_driver(cls, value):
        # Hosted Postgres vendors generally provide a postgresql:// URL. This
        # app uses SQLAlchemy's async engine, which needs the asyncpg driver.
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+asyncpg://", 1)
            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    @model_validator(mode="after")
    def production_configuration(self):
        if self.environment == "production":
            if self.jwt_secret.startswith("replace_") or len(set(self.jwt_secret)) < 12:
                raise ValueError("Production requires a strong generated JWT_SECRET")
            if "*" in self.cors_origins:
                raise ValueError("Production CORS origins must be explicit")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
