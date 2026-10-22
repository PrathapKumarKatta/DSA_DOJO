import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.v1 import auth, projects, tasks, workspaces
from app.core.config import get_settings
from app.db.session import get_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()  # Validate secrets before serving any requests.
    yield
    await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TaskFlow API",
        version="1.0.0",
        lifespan=lifespan,
        description="Collaborative task management with workspace roles and versioned updates.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    for router in (auth.router, workspaces.router, projects.router, tasks.router):
        app.include_router(router, prefix="/api/v1")

    @app.exception_handler(IntegrityError)
    async def integrity_error(request: Request, exc: IntegrityError):
        return JSONResponse(
            status_code=409, content={"detail": "Conflicting or invalid database reference"}
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        logger.error("Database operation failed: %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable"})

    @app.get("/health", tags=["Operations"])
    async def health():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["Operations"])
    async def readiness():
        try:
            async with get_engine().connect() as connection:
                await connection.execute(text("SELECT 1"))
                await connection.execute(text("SELECT version_num FROM alembic_version"))
            async with Redis.from_url(
                settings.redis_url, socket_connect_timeout=2, socket_timeout=2
            ) as redis:
                await redis.ping()
        except (SQLAlchemyError, RedisError, OSError):
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        return {"status": "ready"}

    return app


app = create_app()
