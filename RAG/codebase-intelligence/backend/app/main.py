from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api import auth, projects, health, ingestion, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure storage directories exist
    settings.storage_path
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Production-grade AI Codebase Intelligence Assistant RAG API",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    logger.info(f"HTTP {request.method} {request.url.path}")
    response = await call_next(request)
    return response

# Include routers
app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(ingestion.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)


@app.get("/", include_in_schema=False)
def root():
    return {
        "name": settings.APP_NAME,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health/live",
    }
