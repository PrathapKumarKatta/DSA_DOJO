from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from app.core.config import settings
from app.db.session import get_db
from app.core.logging import logger

router = APIRouter(tags=["health"])


@router.get("/health/live", summary="Liveness probe")
def health_live():
    return {"status": "ok", "service": "codebase-intelligence"}


@router.get("/health/ready", summary="Readiness probe")
def health_ready(response: Response, db: Session = Depends(get_db)):
    readiness = {
        "status": "ready",
        "database": "unknown",
        "redis": "unknown",
    }
    # Check Database
    try:
        db.execute(text("SELECT 1"))
        readiness["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        readiness["database"] = f"error: {str(e)}"
        readiness["status"] = "unhealthy"

    # Check Redis
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        r.ping()
        readiness["redis"] = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        readiness["redis"] = f"error: {str(e)}"
        readiness["status"] = "unhealthy"

    if readiness["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return readiness
