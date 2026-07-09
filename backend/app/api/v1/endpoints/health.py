from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.core.config import settings
import redis.asyncio as aioredis
import time
import platform

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check for load balancers and monitoring."""
    start = time.time()
    checks = {}
    healthy = True

    # Database check
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
        healthy = False
    checks["database"] = db_status

    # Redis check
    try:
        r = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            socket_connect_timeout=2,
            decode_responses=True,
        )
        r.ping()
        redis_status = "healthy"
    except Exception:
        redis_status = "unhealthy"
        healthy = False
    checks["redis"] = redis_status

    response_time = time.time() - start

    return {
        "status": "healthy" if healthy else "degraded",
        "version": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time(),
        "response_time_ms": round(response_time * 1000, 2),
        "python_version": platform.python_version(),
        "checks": checks,
    }


@router.get("/health/ready")
def readiness_check():
    """Readiness probe - service is ready to accept traffic."""
    return {"status": "ready"}


@router.get("/health/live")
def liveness_check():
    """Liveness probe - service is alive."""
    return {"status": "alive"}
