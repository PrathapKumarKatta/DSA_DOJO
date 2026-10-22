import os
from pydantic import BaseModel


class Config(BaseModel):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/app_db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "prod-secret-key-999")
    PAYMENT_GATEWAY_URL: str = "https://api.payment-gateway.internal/v1"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60


config = Config()
